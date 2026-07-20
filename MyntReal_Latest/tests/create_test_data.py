"""
Create temporary test data for E2E testing
Records will be marked with special related_user_id for easy cleanup
"""
import os
import sys
sys.path.insert(0, 'backend')

from sqlalchemy import create_engine, text
from datetime import datetime, date

DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)

# Marker for test records - use a special ID that doesn't exist
TEST_MARKER_ID = 'TEST_E2E_DELETE'

def create_test_data():
    """Create test income records"""
    with engine.begin() as conn:
        # Create test incomes with ≥ ₹1,000 withdrawable (will create "Pending" withdrawals)
        result1 = conn.execute(text("""
            INSERT INTO pending_income (
                user_id, 
                income_type, 
                gross_amount, 
                admin_deduction,
                tds_deduction,
                net_amount,
                withdrawal_wallet_amount,
                upgraded_wallet_amount,
                business_date, 
                verification_status,
                calculation_timestamp,
                created_at,
                updated_at,
                related_user_id
            )
            SELECT 
                id,
                'Direct Referral',
                2500.00,
                200.00,
                50.00,
                2200.00,
                1100.00,
                1100.00,
                CURRENT_DATE,
                'Pending',
                NOW(),
                NOW(),
                NOW(),
                :marker
            FROM "user"
            WHERE id LIKE 'BEV18%'
            AND id NOT IN ('BEV182364369', 'BEV182322707', 'BEV182371007', 'BEV182371010')
            LIMIT 5
            RETURNING id, user_id, withdrawal_wallet_amount
        """), {"marker": TEST_MARKER_ID})
        
        test_ids_high = [row[0] for row in result1]
        print(f"✅ Created {len(test_ids_high)} test incomes (≥ ₹1,000)")
        
        # Create test incomes with < ₹1,000 withdrawable (will create "On Hold" withdrawals)
        result2 = conn.execute(text("""
            INSERT INTO pending_income (
                user_id, 
                income_type, 
                gross_amount, 
                admin_deduction,
                tds_deduction,
                net_amount,
                withdrawal_wallet_amount,
                upgraded_wallet_amount,
                business_date, 
                verification_status,
                calculation_timestamp,
                created_at,
                updated_at,
                related_user_id
            )
            SELECT 
                id,
                'Matching Referral',
                800.00,
                64.00,
                16.00,
                704.00,
                352.00,
                352.00,
                CURRENT_DATE,
                'Pending',
                NOW(),
                NOW(),
                NOW(),
                :marker
            FROM "user"
            WHERE id LIKE 'BEV18%'
            AND id NOT IN ('BEV182364369', 'BEV182322707', 'BEV182371007', 'BEV182371010')
            AND id NOT IN (SELECT user_id FROM pending_income WHERE related_user_id = :marker)
            LIMIT 3
            RETURNING id, user_id, withdrawal_wallet_amount
        """), {"marker": TEST_MARKER_ID})
        
        test_ids_low = [row[0] for row in result2]
        print(f"✅ Created {len(test_ids_low)} test incomes (< ₹1,000)")
        
        # Verify
        verify = conn.execute(text("""
            SELECT COUNT(*), SUM(gross_amount), SUM(withdrawal_wallet_amount)
            FROM pending_income
            WHERE related_user_id = :marker
        """), {"marker": TEST_MARKER_ID}).fetchone()
        
        print(f"\n📊 Test Data Summary:")
        print(f"   Total Records: {verify[0]}")
        print(f"   Total Gross: ₹{verify[1]:,.2f}")
        print(f"   Total Withdrawable: ₹{verify[2]:,.2f}")
        print(f"\n🔖 Test Marker ID: {TEST_MARKER_ID}")
        
        return test_ids_high + test_ids_low

if __name__ == "__main__":
    test_ids = create_test_data()
    print(f"\n✅ Test data created successfully!")
    print(f"📝 Test Record IDs: {test_ids}")
