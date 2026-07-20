"""
Save Matching Income to Database for All Active Users

This script calculates and SAVES matching income to pending_income table
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from decimal import Decimal

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

def save_matching_income():
    print("\n" + "="*60)
    print("SAVING MATCHING INCOME TO DATABASE")
    print("="*60)
    
    month = datetime.now().strftime("%Y-%m")
    
    # Get all active users with placements
    query = text("""
        SELECT DISTINCT u.id, u.name, u.package_points
        FROM "user" u
        INNER JOIN placement p ON u.id = p.child_id
        WHERE u.account_status = 'Active'
          AND u.package_points > 0
        ORDER BY u.id
    """)
    
    users = db.execute(query).fetchall()
    print(f"Processing {len(users)} active users...")
    
    from app.services.reference_service import ReferenceService
    from app.models.transaction import PendingIncome
    reference_service = ReferenceService(db)
    
    total_saved = Decimal('0.00')
    users_saved = 0
    
    for user in users:
        user_id = user.id
        
        try:
            # Calculate matching income
            result = reference_service.calculate_matching_referral_income(user_id, month)
            income = Decimal(str(result.get('total_income', 0)))
            status = result.get('income_status', 'unknown')
            
            if income > 0:
                # Check if already saved for this month
                business_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                existing = db.query(PendingIncome).filter(
                    PendingIncome.user_id == user_id,
                    PendingIncome.income_type == 'Matching Referral',
                    PendingIncome.business_date == business_date
                ).first()
                
                if not existing:
                    # Calculate deductions
                    gross = income
                    admin_deduction = gross * Decimal('0.08')  # 8% admin + 2% TDS = 10% total
                    tds_deduction = gross * Decimal('0.02')  # 2% TDS
                    net = gross - admin_deduction - tds_deduction
                    
                    # Split based on package (Platinum = 100% withdrawal, others split)
                    if user.package_points == 1.0:  # Platinum
                        withdrawal_wallet = net
                        upgraded_wallet = Decimal('0')
                    else:  # Diamond, others
                        withdrawal_wallet = net * Decimal('0.5')
                        upgraded_wallet = net * Decimal('0.5')
                    
                    # Create pending income record
                    pending = PendingIncome(
                        user_id=user_id,
                        income_type='Matching Referral',
                        gross_amount=float(gross),
                        admin_deduction=float(admin_deduction),
                        tds_deduction=float(tds_deduction),
                        net_amount=float(net),
                        withdrawal_wallet_amount=float(withdrawal_wallet),
                        upgraded_wallet_amount=float(upgraded_wallet),
                        business_date=business_date,
                        calculation_timestamp=datetime.now(),
                        verification_status='pending' if status == 'held_pending_eligibility' else 'approved',
                        created_at=datetime.now()
                    )
                    
                    db.add(pending)
                    total_saved += net
                    users_saved += 1
                    
                    print(f"  ✅ {user_id}: ₹{float(gross):.2f} → ₹{float(net):.2f} net ({status})")
                else:
                    print(f"  ⏭️  {user_id}: Already saved")
        
        except Exception as e:
            print(f"  ❌ {user_id}: {str(e)}")
    
    # Commit all
    db.commit()
    
    print(f"\n" + "="*60)
    print(f"✅ SAVED: ₹{float(total_saved):,.2f} net income for {users_saved} users")
    print(f"Total records created: {users_saved}")
    print("="*60)

if __name__ == "__main__":
    try:
        save_matching_income()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
