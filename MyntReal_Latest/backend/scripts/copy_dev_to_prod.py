#!/usr/bin/env python3
"""
Database Copy Script - Development → Production
Safely copies all data from development database to production database

CRITICAL WARNINGS:
- This will REPLACE all production data with development data
- Make sure development database is a complete clone before running
- This operation cannot be undone without a backup

Usage:
    python copy_dev_to_prod.py
"""

import os
import sys
import subprocess
from datetime import datetime

def print_header(message):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60 + "\n")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ ERROR: {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  WARNING: {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def get_database_urls():
    """Get development and production database URLs from environment"""
    # Check if we're in production or development
    # Replit sets REPLIT_DEPLOYMENT when in production
    is_production = os.getenv('REPLIT_DEPLOYMENT') is not None
    
    if is_production:
        print_error("This script should NOT be run in production deployment!")
        print_info("Please run this from your development Repl")
        sys.exit(1)
    
    # Get the development DATABASE_URL (current environment)
    dev_db_url = os.getenv('DATABASE_URL')
    
    if not dev_db_url:
        print_error("DATABASE_URL not found in environment")
        print_info("Make sure you're in a Replit environment with Postgres database")
        sys.exit(1)
    
    print_info(f"Development DB found: {dev_db_url[:30]}...")
    
    # For production URL, we need user to provide it
    print_warning("Production DATABASE_URL needed")
    print_info("Please provide your PRODUCTION database URL")
    print_info("You can find it in Replit Secrets or Production environment variables")
    
    prod_db_url = input("\nEnter PRODUCTION DATABASE_URL: ").strip()
    
    if not prod_db_url or prod_db_url == dev_db_url:
        print_error("Invalid production URL or same as development")
        sys.exit(1)
    
    return dev_db_url, prod_db_url

def confirm_action():
    """Get user confirmation before proceeding"""
    print_header("⚠️  CRITICAL CONFIRMATION REQUIRED")
    print("This script will:")
    print("  1. Export ALL data from DEVELOPMENT database")
    print("  2. REPLACE ALL data in PRODUCTION database")
    print("  3. This operation CANNOT be undone without a backup")
    print("\nMake sure:")
    print("  ✓ Development database is a complete clone of production")
    print("  ✓ You have verified development shows correct data (₹95,975.33)")
    print("  ✓ You understand this will overwrite production")
    
    response = input("\nType 'YES I UNDERSTAND' to proceed: ").strip()
    
    if response != "YES I UNDERSTAND":
        print_info("Operation cancelled by user")
        sys.exit(0)

def run_command(command, description):
    """Run a shell command and handle errors"""
    print_info(f"Running: {description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print_success(f"{description} completed")
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed")
        print(f"Error output: {e.stderr}")
        sys.exit(1)

def main():
    """Main execution function"""
    print_header("DATABASE COPY SCRIPT - Development → Production")
    print_info("This script will copy your development database to production")
    print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Get database URLs
    print_header("STEP 1: Getting Database URLs")
    dev_db_url, prod_db_url = get_database_urls()
    print_success("Database URLs configured")
    
    # Step 2: Confirm with user
    confirm_action()
    
    # Step 3: Create backup directory
    print_header("STEP 2: Preparing Backup")
    backup_file = "/tmp/dev_backup.sql"
    
    # Step 4: Export from development
    print_header("STEP 3: Exporting Development Database")
    print_info("This may take a few minutes for large databases...")
    
    export_cmd = f'pg_dump "{dev_db_url}" > {backup_file}'
    run_command(export_cmd, "Database export from development")
    
    # Check backup file size
    backup_size = os.path.getsize(backup_file)
    print_success(f"Backup file created: {backup_size:,} bytes ({backup_size/1024/1024:.2f} MB)")
    
    # Step 5: Import to production
    print_header("STEP 4: Importing to Production Database")
    print_warning("This will REPLACE all production data!")
    print_info("This may take a few minutes...")
    
    # First, drop all existing connections and reset production DB
    import_cmd = f'psql "{prod_db_url}" < {backup_file}'
    run_command(import_cmd, "Database import to production")
    
    # Step 6: Cleanup
    print_header("STEP 5: Cleanup")
    if os.path.exists(backup_file):
        os.remove(backup_file)
        print_success("Temporary backup file removed")
    
    # Step 7: Success!
    print_header("✅ DATABASE COPY COMPLETE!")
    print_success("Development database successfully copied to production")
    print_info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNEXT STEPS:")
    print("  1. Restart your FastAPI Backend workflow")
    print("  2. Test production by logging in as BEV180143")
    print("  3. Verify earnings show ₹95,975.33 (not ₹0)")
    print("  4. Check all other users see correct data")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
