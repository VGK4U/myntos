#!/usr/bin/env python3
"""
Manual Trigger Script for ALL Income Calculations
Runs: Direct Referral, Matching, Ved, Guru Dakshina, Awards, Field Allowances, Bonanzas, Wallet Sync
"""

import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.scheduler import (
    calculate_previous_day_incomes,
    calculate_monthly_field_allowances,
    run_daily_wallet_sync,
    refresh_leg_metrics_cache,
    generate_automatic_withdrawals
)

def main():
    """
    Manually trigger ALL income calculations, awards, allowances, and bonanzas
    """
    print("=" * 80)
    print("🚀 MANUAL TRIGGER: ALL INCOME CALCULATIONS")
    print("=" * 80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Step 1: Refresh Leg Metrics Cache (FIRST - required for accurate calculations)
        print("📊 STEP 1: Refreshing Leg Metrics Cache...")
        print("-" * 80)
        refresh_leg_metrics_cache()
        print("✅ Leg metrics cache refreshed successfully")
        print()
        
        # Step 2: Calculate ALL Income Types (Direct, Matching, Ved, Guru Dakshina, Awards)
        print("💰 STEP 2: Calculating ALL Income Types...")
        print("-" * 80)
        calculate_previous_day_incomes()
        print("✅ All income types calculated successfully")
        print()
        
        # Step 3: Calculate Monthly Field Allowances (Standard, Car, Jaguar)
        print("🚗 STEP 3: Calculating Field Allowances...")
        print("-" * 80)
        calculate_monthly_field_allowances()
        print("✅ Field allowances calculated successfully")
        print()
        
        # Step 4: Run Daily Wallet Sync (earning_wallet → withdrawable_wallet for KYC approved users)
        print("💳 STEP 4: Running Daily Wallet Sync (KYC Enforcement)...")
        print("-" * 80)
        run_daily_wallet_sync()
        print("✅ Wallet sync completed successfully")
        print()
        
        # Step 5: Generate Automatic Withdrawals (for eligible users)
        print("💸 STEP 5: Generating Automatic Withdrawals...")
        print("-" * 80)
        generate_automatic_withdrawals()
        print("✅ Automatic withdrawals generated successfully")
        print()
        
        # Summary
        print("=" * 80)
        print("✅ ALL CALCULATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📋 Summary of Executed Jobs:")
        print("   1. ✅ Leg Metrics Cache Refresh")
        print("   2. ✅ Income Calculations (Direct, Matching, Ved, Guru Dakshina)")
        print("   3. ✅ Awards Income (Direct Awards, Matching Awards)")
        print("   4. ✅ Field Allowances (Standard, Car, Jaguar)")
        print("   5. ✅ Wallet Sync (earning_wallet → withdrawable_wallet)")
        print("   6. ✅ Automatic Withdrawals Generated")
        print()
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR DURING CALCULATIONS!")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
