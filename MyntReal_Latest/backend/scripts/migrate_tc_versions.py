"""
Database Migration Script: Create T&C Versions Table and Migrate Data
Run this once to set up the new Terms & Conditions version management system
"""

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.system_control import TermsAndConditionsVersion, AppSettings
from app.models.base import Base

def migrate_tc_versions():
    """Create T&C versions table and migrate existing data"""
    
    print("🔄 Starting T&C Version Management Migration...")
    
    # Get database URL from settings
    db_url = str(settings.DATABASE_URL)
    print(f"📊 Database: {db_url.split('@')[1] if '@' in db_url else 'local'}")
    
    engine = create_engine(db_url)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Step 1: Create the table
        print("\n📋 Step 1: Creating terms_and_conditions_versions table...")
        Base.metadata.create_all(bind=engine, tables=[TermsAndConditionsVersion.__table__])
        print("✅ Table created successfully")
        
        # Step 2: Check if migration needed
        print("\n📋 Step 2: Checking for existing versions...")
        existing_versions = db.query(TermsAndConditionsVersion).count()
        
        if existing_versions > 0:
            print(f"✅ Found {existing_versions} existing version(s), skipping migration")
            return True
        
        # Step 3: Migrate from app_settings
        print("\n📋 Step 3: Migrating T&C from app_settings...")
        success = TermsAndConditionsVersion.migrate_from_app_settings(db)
        
        if success:
            print("✅ Migration completed successfully")
            
            # Step 4: Verify migration
            print("\n📋 Step 4: Verifying migration...")
            active_version = TermsAndConditionsVersion.get_active_version(db)
            
            if active_version:
                print(f"✅ Active version: {active_version.version}")
                print(f"   Created by: {active_version.created_by}")
                print(f"   Content length: {len(active_version.content)} characters")
                print(f"   Max displays: {active_version.max_displays}")
            else:
                print("⚠️ Warning: No active version found")
                return False
            
            return True
        else:
            print("❌ Migration failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
        engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("T&C VERSION MANAGEMENT MIGRATION")
    print("=" * 60)
    
    success = migrate_tc_versions()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ MIGRATION SUCCESSFUL")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart the FastAPI Backend workflow")
        print("2. Test T&C version endpoints")
        print("3. Update frontend to use new version management")
    else:
        print("❌ MIGRATION FAILED")
        print("=" * 60)
        print("\nPlease check the error messages above")
    
    sys.exit(0 if success else 1)
