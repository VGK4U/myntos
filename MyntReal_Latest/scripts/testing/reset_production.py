#!/usr/bin/env python3
"""
Production Database Reset Script
Resets all earnings to ₹0 in production database
"""

import os
import sys
import subprocess

def main():
    print("🔄 Production Database Reset")
    print("=" * 50)
    print()
    
    # Get production database URL from environment
    prod_db_url = os.getenv('PRODUCTION_DATABASE_URL')
    
    if not prod_db_url:
        print("❌ ERROR: PRODUCTION_DATABASE_URL not found!")
        print()
        print("Please set your production database URL:")
        print()
        print("1. Go to your deployed app settings")
        print("2. Copy the production DATABASE_URL")
        print("3. Run: export PRODUCTION_DATABASE_URL='your-url'")
        print("4. Run this script again")
        sys.exit(1)
    
    # Path to SQL script
    sql_script = 'backend/PRODUCTION_RESET_SCRIPT.sql'
    
    if not os.path.exists(sql_script):
        print(f"❌ ERROR: Script not found: {sql_script}")
        sys.exit(1)
    
    print(f"📊 Connecting to production database...")
    print(f"📄 Running: {sql_script}")
    print()
    
    # Run the SQL script
    try:
        result = subprocess.run(
            ['psql', prod_db_url, '-f', sql_script],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ Warnings/Info:")
            print(result.stderr)
        
        print()
        print("✅ Reset completed successfully!")
        print()
        print("📋 Next steps:")
        print("1. Check the verification results above")
        print("2. All values should be 0")
        print("3. Visit https://app.bevseries.com and hard refresh")
        
    except subprocess.CalledProcessError as e:
        print("❌ ERROR during reset:")
        print(e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("❌ ERROR: 'psql' command not found!")
        print("Please install PostgreSQL client tools")
        sys.exit(1)

if __name__ == '__main__':
    main()
