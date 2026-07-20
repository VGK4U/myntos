"""
Trigger All Income Calculations - Run after user upload
Calculates: Direct, Matching, Ved, Guru Dakshina, Awards, Bonanza, Field Allowances
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.core.scheduler import (
    calculate_previous_day_incomes,
    calculate_monthly_field_allowances
)
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Trigger all income calculations"""
    print("=" * 80)
    print("TRIGGER ALL INCOME CALCULATIONS")
    print("=" * 80)
    
    try:
        # Step 1: Calculate Daily Incomes (Direct, Matching, Ved, Guru Dakshina, Awards, Bonanza)
        print("\n📊 Step 1: Calculating Daily Incomes...")
        print("   - Direct Referral Income")
        print("   - Matching Referral Income")
        print("   - Ved Income (NO CASCADING)")
        print("   - Guru Dakshina (2% of referrals' earnings)")
        print("   - Awards (Direct & Matching)")
        print("   - Bonanza Rewards")
        print("")
        
        calculate_previous_day_incomes()
        print("   ✅ Daily incomes calculated successfully!")
        
        # Step 2: Calculate Monthly Field Allowances
        print("\n📊 Step 2: Calculating Field Allowances...")
        print("   - Standard Field Allowance (₹10,000/month for 36 months)")
        print("   - Car Allowance (₹25,000/month for 72 months)")
        print("")
        
        calculate_monthly_field_allowances()
        print("   ✅ Field allowances calculated successfully!")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ ALL INCOME CALCULATIONS COMPLETE!")
        print("=" * 80)
        print("")
        print("📋 Summary:")
        print("   ✓ Direct Referral Income")
        print("   ✓ Matching Referral Income (with ceiling)")
        print("   ✓ Ved Income (NO CASCADING rule applied)")
        print("   ✓ Guru Dakshina (2% deduction)")
        print("   ✓ Direct Awards (7 levels)")
        print("   ✓ Matching Awards (12 levels)")
        print("   ✓ Bonanza Rewards")
        print("   ✓ Field Allowances (Standard + Car)")
        print("")
        print("💰 All pending incomes created with:")
        print("   - Deductions applied (Admin 8% + TDS 2%)")
        print("   - Guru Dakshina deducted (2% to referrer)")
        print("   - Wallet splits applied (based on package)")
        print("   - ₹50,000 daily ceiling enforced (Ved+Matching)")
        print("")
        print("🔄 Next Steps:")
        print("   1. Review pending incomes in admin panel")
        print("   2. Verify income calculations")
        print("   3. Approve incomes (or they auto-approve if configured)")
        print("")
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        raise

if __name__ == "__main__":
    main()
