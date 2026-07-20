#!/usr/bin/env python3
"""
ONE-TIME FIX SCRIPT: Fix Package Data
Corrects package_points and coupon_status for all activated users
Run this ONCE on production after deployment
"""

import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def fix_package_data():
    """Fix package_points and coupon_status for activated users"""
    
    # Create database connection
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("🔍 Checking for users needing package data fix...")
        
        # Check how many users need fixing
        check_query = text("""
            SELECT COUNT(*) 
            FROM "user" 
            WHERE activation_date IS NOT NULL 
              AND (package_points != 1.0 OR coupon_status IN ('Activated', 'Eligible', 'Active'))
        """)
        result = db.execute(check_query)
        users_needing_fix = result.scalar()
        
        if users_needing_fix == 0:
            print("✅ All users already have correct package data!")
            return
        
        print(f"📊 Found {users_needing_fix} users needing fix")
        
        # Fix package_points
        print("\n🔧 Fixing package_points...")
        package_fix_query = text("""
            UPDATE "user" 
            SET package_points = 1.0 
            WHERE activation_date IS NOT NULL 
              AND (package_points IS NULL OR package_points = 0.0)
        """)
        package_result = db.execute(package_fix_query)
        db.commit()
        print(f"   ✅ Updated package_points for {package_result.rowcount} users")
        
        # Fix coupon_status
        print("\n🔧 Fixing coupon_status...")
        coupon_fix_query = text("""
            UPDATE "user" 
            SET coupon_status = 'Platinum'
            WHERE activation_date IS NOT NULL 
              AND coupon_status IN ('Activated', 'Eligible', 'Active')
        """)
        coupon_result = db.execute(coupon_fix_query)
        db.commit()
        print(f"   ✅ Updated coupon_status for {coupon_result.rowcount} users")
        
        # Verify fix
        print("\n🔍 Verifying fix...")
        verify_query = text("""
            SELECT COUNT(*) 
            FROM "user" 
            WHERE activation_date IS NOT NULL 
              AND (package_points != 1.0 OR coupon_status IN ('Activated', 'Eligible', 'Active'))
        """)
        verify_result = db.execute(verify_query)
        remaining_issues = verify_result.scalar()
        
        if remaining_issues == 0:
            print("✅ SUCCESS! All activated users now show Platinum package")
            
            # Show sample user
            sample_query = text("""
                SELECT id, name, package_points, coupon_status 
                FROM "user" 
                WHERE activation_date IS NOT NULL 
                LIMIT 5
            """)
            sample_result = db.execute(sample_query)
            print("\n📋 Sample users after fix:")
            for row in sample_result:
                print(f"   {row.id}: {row.name} - Points: {row.package_points}, Status: {row.coupon_status}")
        else:
            print(f"⚠️  WARNING: {remaining_issues} users still have issues")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 BeV 2.0 Package Data Fix")
    print("=" * 60)
    fix_package_data()
    print("\n" + "=" * 60)
    print("✅ Fix Complete!")
    print("=" * 60)
