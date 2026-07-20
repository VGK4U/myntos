"""
Comprehensive Income Calculation Script for All Users

Calculates:
1. Direct Referral Income
2. Matching Referral Income  
3. Ved Income
4. Guru Dakshina
5. Direct Awards
6. Matching Awards
7. Field Allowances
8. Car Allowances
9. Bonanza Progress

For all active users in the system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from decimal import Decimal
import traceback

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

def get_current_month():
    """Get current month in YYYY-MM format"""
    return datetime.now().strftime("%Y-%m")

def calculate_direct_income():
    """Calculate direct referral income for all users"""
    print("\n" + "="*60)
    print("CALCULATING DIRECT REFERRAL INCOME")
    print("="*60)
    
    month = get_current_month()
    
    # Get all users with active referrals this month
    query = text("""
        SELECT DISTINCT u.referrer_id
        FROM "user" u
        WHERE u.referrer_id IS NOT NULL
          AND u.referrer_id != ''
          AND u.activation_date >= DATE_TRUNC('month', CURRENT_DATE)
          AND u.account_status = 'Active'
    """)
    
    referrers = db.execute(query).fetchall()
    print(f"Found {len(referrers)} users with active referrals this month")
    
    total_income = Decimal('0.00')
    users_processed = 0
    
    for row in referrers:
        referrer_id = row.referrer_id
        
        # Calculate income for this referrer
        from app.services.reference_service import ReferenceService
        reference_service = ReferenceService(db)
        
        try:
            result = reference_service.calculate_direct_referral_income(referrer_id, month)
            if result.get('total_income', 0) > 0:
                total_income += Decimal(str(result['total_income']))
                users_processed += 1
                print(f"  ✅ {referrer_id}: ₹{result['total_income']:.2f}")
        except Exception as e:
            print(f"  ❌ {referrer_id}: {str(e)}")
    
    print(f"\n✅ Direct Income Calculated: ₹{total_income:.2f} for {users_processed} users")
    return float(total_income)

def calculate_matching_income():
    """Calculate matching referral income for all users"""
    print("\n" + "="*60)
    print("CALCULATING MATCHING REFERRAL INCOME")
    print("="*60)
    
    month = get_current_month()
    
    # Get all active users with placements
    query = text("""
        SELECT DISTINCT u.id, u.name
        FROM "user" u
        INNER JOIN placement p ON u.id = p.child_id
        WHERE u.account_status = 'Active'
          AND u.package_points > 0
        ORDER BY u.id
    """)
    
    users = db.execute(query).fetchall()
    print(f"Found {len(users)} active users for matching income calculation")
    
    total_income = Decimal('0.00')
    users_with_income = 0
    
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    
    for user in users:
        user_id = user.id
        
        try:
            result = reference_service.calculate_matching_referral_income(user_id, month)
            income = result.get('total_income', 0)
            
            if income > 0:
                total_income += Decimal(str(income))
                users_with_income += 1
                status = result.get('income_status', 'unknown')
                print(f"  ✅ {user_id}: ₹{income:.2f} ({status})")
        except Exception as e:
            print(f"  ❌ {user_id}: {str(e)}")
    
    print(f"\n✅ Matching Income Calculated: ₹{total_income:.2f} for {users_with_income} users")
    return float(total_income)

def calculate_ved_income():
    """Calculate Ved income for all Ved owners"""
    print("\n" + "="*60)
    print("CALCULATING VED INCOME")
    print("="*60)
    
    month = get_current_month()
    
    # Get all users who own Ved members
    query = text("""
        SELECT DISTINCT u.id, u.name
        FROM "user" u
        WHERE EXISTS (
            SELECT 1 FROM "user" ved
            WHERE ved.ved_owner_id = u.id
              AND ved.is_ved = true
        )
        AND u.account_status = 'Active'
        ORDER BY u.id
    """)
    
    ved_owners = db.execute(query).fetchall()
    print(f"Found {len(ved_owners)} Ved owners")
    
    total_income = Decimal('0.00')
    owners_with_income = 0
    
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    
    for owner in ved_owners:
        user_id = owner.id
        
        try:
            result = reference_service.calculate_ved_income(user_id, month)
            income = result.get('total_ved_income', 0)
            
            if income > 0:
                total_income += Decimal(str(income))
                owners_with_income += 1
                print(f"  ✅ {user_id}: ₹{income:.2f}")
        except Exception as e:
            print(f"  ❌ {user_id}: {str(e)}")
    
    print(f"\n✅ Ved Income Calculated: ₹{total_income:.2f} for {owners_with_income} users")
    return float(total_income)

def calculate_awards():
    """Calculate Direct and Matching Awards for all users"""
    print("\n" + "="*60)
    print("CALCULATING AWARDS")
    print("="*60)
    
    # Get all active users
    query = text("""
        SELECT id, name FROM "user"
        WHERE account_status = 'Active'
          AND package_points > 0
        ORDER BY id
    """)
    
    users = db.execute(query).fetchall()
    print(f"Checking awards for {len(users)} active users")
    
    from app.services.award_service import AwardService
    award_service = AwardService(db)
    
    direct_awards = 0
    matching_awards = 0
    
    for user in users:
        user_id = user.id
        
        try:
            # Check and update direct awards
            award_service.check_and_update_direct_awards(user_id)
            
            # Check and update matching awards
            award_service.check_and_update_matching_awards(user_id)
            
            # Get current status
            progress = award_service.get_award_progress(user_id)
            
            if progress.get('current_direct_award'):
                direct_awards += 1
            if progress.get('current_matching_award'):
                matching_awards += 1
                
        except Exception as e:
            print(f"  ❌ {user_id}: {str(e)}")
    
    print(f"\n✅ Awards Updated:")
    print(f"   Direct Awards: {direct_awards} users")
    print(f"   Matching Awards: {matching_awards} users")
    
    return {"direct": direct_awards, "matching": matching_awards}

def calculate_field_allowances():
    """Calculate Field Allowances for eligible users"""
    print("\n" + "="*60)
    print("CALCULATING FIELD ALLOWANCES")
    print("="*60)
    
    # Get all active users
    query = text("""
        SELECT id, name FROM "user"
        WHERE account_status = 'Active'
        ORDER BY id
    """)
    
    users = db.execute(query).fetchall()
    print(f"Checking field allowances for {len(users)} users")
    
    from app.services.field_allowance_service import FieldAllowanceService
    fa_service = FieldAllowanceService(db)
    
    standard_fa = 0
    car_allowance = 0
    
    for user in users:
        user_id = user.id
        
        try:
            # Update field allowance progress
            fa_service.update_field_allowance_progress(user_id)
            
            # Update car allowance progress
            fa_service.update_car_allowance_progress(user_id)
            
            # Get eligibility
            fa_elig = fa_service.check_field_allowance_eligibility(user_id)
            ca_elig = fa_service.check_car_allowance_eligibility(user_id)
            
            if fa_elig.get('is_eligible'):
                standard_fa += 1
            if ca_elig.get('is_eligible'):
                car_allowance += 1
                
        except Exception as e:
            print(f"  ❌ {user_id}: {str(e)}")
    
    print(f"\n✅ Field Allowances Calculated:")
    print(f"   Standard Field Allowance: {standard_fa} eligible users")
    print(f"   Car Allowance: {car_allowance} eligible users")
    
    return {"standard": standard_fa, "car": car_allowance}

def calculate_bonanza():
    """Calculate Bonanza progress for active bonanzas"""
    print("\n" + "="*60)
    print("CALCULATING BONANZA PROGRESS")
    print("="*60)
    
    # Check for active bonanzas
    query = text("""
        SELECT id, title, start_date, end_date
        FROM bonanza
        WHERE status = 'active'
          AND start_date <= CURRENT_DATE
          AND end_date >= CURRENT_DATE
    """)
    
    bonanzas = db.execute(query).fetchall()
    
    if not bonanzas:
        print("No active bonanzas found")
        return 0
    
    print(f"Found {len(bonanzas)} active bonanzas")
    
    from app.services.bonanza_service import BonanzaService
    bonanza_service = BonanzaService(db)
    
    participants = 0
    
    for bonanza in bonanzas:
        bonanza_id = bonanza.id
        print(f"\nProcessing: {bonanza.title}")
        
        try:
            # Update progress for all participants
            bonanza_service.update_all_bonanza_progress(bonanza_id)
            
            # Get participant count
            count_query = text("""
                SELECT COUNT(DISTINCT user_id) as count
                FROM bonanza_progress
                WHERE bonanza_id = :bonanza_id
            """)
            count = db.execute(count_query, {"bonanza_id": bonanza_id}).fetchone().count
            participants += count
            print(f"  ✅ Updated progress for {count} participants")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print(f"\n✅ Bonanza Progress Updated for {participants} total participants")
    return participants

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("COMPREHENSIVE INCOME & REWARDS CALCULATION")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Month: {get_current_month()}")
    print("="*80)
    
    try:
        # Step 1: Calculate Direct Income
        direct_total = calculate_direct_income()
        
        # Step 2: Calculate Matching Income
        matching_total = calculate_matching_income()
        
        # Step 3: Calculate Ved Income
        ved_total = calculate_ved_income()
        
        # Step 4: Calculate Awards
        awards = calculate_awards()
        
        # Step 5: Calculate Field Allowances
        allowances = calculate_field_allowances()
        
        # Step 6: Calculate Bonanza
        bonanza_count = calculate_bonanza()
        
        # Final Summary
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)
        print(f"💰 INCOME TOTALS:")
        print(f"   Direct Referral Income:     ₹{direct_total:,.2f}")
        print(f"   Matching Referral Income:   ₹{matching_total:,.2f}")
        print(f"   Ved Income:                 ₹{ved_total:,.2f}")
        print(f"   TOTAL INCOME:               ₹{(direct_total + matching_total + ved_total):,.2f}")
        print(f"\n🏆 AWARDS:")
        print(f"   Direct Awards:              {awards['direct']} users")
        print(f"   Matching Awards:            {awards['matching']} users")
        print(f"\n🚗 ALLOWANCES:")
        print(f"   Field Allowance:            {allowances['standard']} users")
        print(f"   Car Allowance:              {allowances['car']} users")
        print(f"\n🎁 BONANZA:")
        print(f"   Active Participants:        {bonanza_count}")
        print("="*80)
        print("\n✅ ALL CALCULATIONS COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(traceback.format_exc())
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
