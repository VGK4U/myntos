#!/usr/bin/env python3
"""
Simple Database Copy Script - Development to Production
Uses pg_dump and psql for reliable full database copy
"""

import subprocess
import sys
from datetime import datetime
import os

DEV_URL = "postgresql://neondb_owner:npg_LYfk0Nre2IKo@ep-bitter-heart-adi4zlxw.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
PROD_URL = "postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

DUMP_FILE = "/tmp/dev_backup.sql"

def print_header():
    print("\n" + "="*70)
    print("  DATABASE COPY SCRIPT - Development → Production")
    print("="*70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def run_command(cmd, description):
    """Run a shell command and show progress"""
    print(f"\n📋 {description}...")
    print(f"   Command: {cmd[:80]}..." if len(cmd) > 80 else f"   Command: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) <= 10:
                for line in lines:
                    print(f"   {line}")
            else:
                print(f"   ... {len(lines)} lines of output ...")
        
        print(f"✅ {description} complete!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"   Error: {e.stderr[:500]}")
        return False

def main():
    print_header()
    
    # Confirm
    print("⚠️  WARNING: This will REPLACE all production data with development data!")
    print()
    print(f"   Development: {DEV_URL[:50]}...")
    print(f"   Production:  {PROD_URL[:50]}...")
    print()
    response = input("Type 'YES' to continue: ").strip()
    
    if response != 'YES':
        print("\n❌ Copy cancelled")
        sys.exit(0)
    
    print("\n🚀 Starting database copy...\n")
    
    # Step 1: Export from development
    export_cmd = f'pg_dump "{DEV_URL}" > {DUMP_FILE}'
    if not run_command(export_cmd, "Export from Development database"):
        sys.exit(1)
    
    # Check file size
    file_size = os.path.getsize(DUMP_FILE)
    print(f"\n📊 Backup file size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    if file_size < 1000:
        print("⚠️  Warning: Backup file is suspiciously small!")
        response = input("Continue anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            print("\n❌ Copy cancelled")
            sys.exit(0)
    
    # Step 2: Import to production
    import_cmd = f'psql "{PROD_URL}" < {DUMP_FILE}'
    if not run_command(import_cmd, "Import to Production database"):
        print("\n⚠️  Import had errors, but may have partially succeeded")
        print("   Check production database manually")
        sys.exit(1)
    
    # Step 3: Clean up
    try:
        os.remove(DUMP_FILE)
        print(f"\n🗑️  Cleaned up temp file: {DUMP_FILE}")
    except:
        pass
    
    # Success!
    print("\n" + "="*70)
    print("  ✅ DATABASE COPY COMPLETE!")
    print("="*70)
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📝 Next steps:")
    print("   1. Restart FastAPI Backend workflow")
    print("   2. Login as BEV180143 in production")
    print("   3. Check earnings → Should show ₹95,975.33 ✅")
    print()

if __name__ == "__main__":
    main()
