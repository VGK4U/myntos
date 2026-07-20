"""
User Upload Script - Replace existing users with Excel data
Preserves admin users and recalculates all incomes
"""

import pandas as pd
import sys
import os
from datetime import datetime, date, time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db, engine
from app.models.user import User

# Excel file path
EXCEL_FILE = "attached_assets/Users5_1760008547564.xlsx"

# Admin user types to preserve
ADMIN_TYPES = ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']

# Activation date for ACTIVATED users (2nd Oct 2025)
ACTIVATION_DATE = datetime(2025, 10, 2, 0, 0, 0)

def excel_serial_to_date(serial_number):
    """Convert Excel serial date to Python date"""
    if pd.isna(serial_number):
        return None
    # Excel epoch is 1900-01-01 (but with 1900 leap year bug)
    excel_epoch = datetime(1899, 12, 30)
    return excel_epoch + pd.Timedelta(days=int(serial_number))

def excel_time_to_time(time_decimal):
    """Convert Excel decimal time to Python time"""
    if pd.isna(time_decimal) or time_decimal == 0:
        return time(0, 0, 0)
    total_seconds = int(time_decimal * 24 * 60 * 60)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return time(hours, minutes, seconds)

def map_package_type(package_type_str):
    """Map Excel PACKAGE TYPE to package_points"""
    if pd.isna(package_type_str):
        return 0.0
    if str(package_type_str).upper() == "PLATINUM COUPON":
        return 1.0
    return 0.0

def map_coupon_status(status_str):
    """Map Excel COUPON/PACKAGE STATUS to coupon_status"""
    if pd.isna(status_str):
        return "Inactive"
    status = str(status_str).upper().strip()
    # Handle all variations of "activated"
    if status in ["ACTIVATED", "ACTIVE"]:
        return "Activated"
    # Handle variations of "inactive" (including 'IN ACTIVE' with space)
    if status in ["INACTIVE", "IN ACTIVE", "DEACTIVATED"]:
        return "Inactive"
    # Default: check if it contains ACTIVE (but not IN ACTIVE)
    if "ACTIVATED" in status or (status == "ACTIVE"):
        return "Activated"
    return "Inactive"

def map_account_status(status_str):
    """Map Excel USER STATUS to account_status (must be exactly 'Active', 'Inactive', 'Locked', or 'Suspended')"""
    if pd.isna(status_str):
        return "Inactive"
    status = str(status_str).upper().strip()
    # Map to exact status values
    if status in ["ACTIVE", "ACTIVATED", "YES", "Y", "1", "TRUE"]:
        return "Active"
    if status in ["LOCKED"]:
        return "Locked"
    if status in ["SUSPENDED", "SUSPEND"]:
        return "Suspended"
    # Map common variations to 'Inactive'
    if status in ["INACTIVE", "IN ACTIVE", "DEACTIVATED", "NO", "N", "0", "FALSE", "BLOCKED"]:
        return "Inactive"
    # Default: if it contains "ACTIVE" (but not "IN ACTIVE"), treat as Active
    if "ACTIVE" in status and "IN ACTIVE" not in status_str.upper():
        return "Active"
    return "Inactive"

def get_admin_users(db: Session):
    """Get list of admin user IDs to preserve"""
    admin_users = db.query(User.id).filter(User.user_type.in_(ADMIN_TYPES)).all()
    admin_ids = [user.id for user in admin_users]
    print(f"\n📋 Found {len(admin_ids)} admin users to preserve:")
    for admin_id in admin_ids:
        admin = db.query(User).filter(User.id == admin_id).first()
        print(f"   - {admin_id}: {admin.name} ({admin.user_type})")
    return admin_ids

def delete_non_admin_users(db: Session, admin_ids: list):
    """Delete all non-admin users and their related data"""
    print(f"\n🗑️  Deleting non-admin users...")
    
    # Get count before deletion
    total_before = db.query(User).count()
    non_admin_count = db.query(User).filter(~User.id.in_(admin_ids)).count()
    
    print(f"   Total users before: {total_before}")
    print(f"   Non-admin users to delete: {non_admin_count}")
    
    # Delete from log tables first (they don't have CASCADE)
    print(f"   Deleting from log tables...")
    log_tables = ['placement_log', 'field_change_log', 'user_action', 'ticket_log', 'menu_audit_logs', 'audit_log']
    for table in log_tables:
        try:
            # Try different possible user_id column names
            for col in ['user_id', 'actor_user_id', 'target_user_id', 'sponsor_user_id', 'new_user_id', 'admin_id']:
                try:
                    # Use parameterized query with tuple expansion
                    placeholders = ','.join([':id' + str(i) for i in range(len(admin_ids))])
                    params = {f'id{i}': admin_ids[i] for i in range(len(admin_ids))}
                    result = db.execute(
                        text(f'DELETE FROM "{table}" WHERE "{col}" NOT IN ({placeholders})'),
                        params
                    )
                    if result.rowcount > 0:
                        print(f"   Cleared {result.rowcount} rows from {table}.{col}")
                    break
                except:
                    continue
        except Exception as e:
            pass  # Skip if table doesn't exist
    
    db.commit()
    
    # Now delete users - foreign keys with CASCADE will handle the rest
    print(f"   Deleting non-admin users...")
    deleted = db.query(User).filter(~User.id.in_(admin_ids)).delete(synchronize_session=False)
    db.commit()
    
    print(f"   ✅ Deleted {deleted} non-admin users")
    print(f"   Remaining users: {db.query(User).count()}")

def import_users_from_excel(db: Session):
    """Import users from Excel file"""
    print(f"\n📥 Importing users from Excel: {EXCEL_FILE}")
    
    # Read Excel (use openpyxl for .xlsx files)
    df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    print(f"   Found {len(df)} users in Excel")
    
    # Track statistics
    imported = 0
    skipped = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            user_id = row['MEMBERID']
            
            # Check if user already exists (admin user)
            existing = db.query(User).filter(User.id == user_id).first()
            if existing:
                print(f"   Skipping existing user: {user_id} ({existing.user_type})")
                skipped += 1
                continue
            
            # Convert dates
            doj_date = excel_serial_to_date(row['DOJ'])
            join_time = excel_time_to_time(row['TIME'])
            
            # Map status and package
            coupon_status = map_coupon_status(row['COUPON / PACKAGE STATUS'])
            package_points = map_package_type(row['PACKAGE TYPE'])
            
            # IMPORTANT: If coupon is Activated, account MUST be Active
            if coupon_status == 'Activated':
                account_status = 'Active'
            else:
                account_status = map_account_status(row['USER STATUS'])
            
            # Determine activation date
            activation_date = ACTIVATION_DATE if coupon_status == 'Activated' else None
            
            # Create user
            new_user = User(
                id=user_id,
                name=str(row['NAME']).strip() if not pd.isna(row['NAME']) else 'Unknown',
                email=str(row['EMAILID']).strip() if not pd.isna(row['EMAILID']) else None,
                password=generate_password_hash(str(row['PASSWORD'])),
                phone_number=str(row['PHONENO']).strip() if not pd.isna(row['PHONENO']) else None,
                user_type='Member',  # All imported users are Members
                referrer_id=str(row['SPONSORID']).strip() if not pd.isna(row['SPONSORID']) else None,
                position_id=str(row['POSITIONID']).strip() if not pd.isna(row['POSITIONID']) else None,
                position=str(row['POSITION']).strip() if not pd.isna(row['POSITION']) else None,
                registration_date=doj_date if doj_date else datetime.now(),
                date_of_joining=doj_date.date() if doj_date else None,
                joining_time=join_time,
                account_status=account_status,
                coupon_status=coupon_status,
                package_points=package_points,
                activation_date=activation_date,
                registration_source='excel_import',
                # Bank details
                bank_account_number=str(row['ACCOUNTNO']) if not pd.isna(row['ACCOUNTNO']) else None,
                bank_name=str(row['BANKNAME']) if not pd.isna(row['BANKNAME']) else None,
                bank_ifsc_code=str(row['IFSC']) if not pd.isna(row['IFSC']) else None,
                bank_branch_name=str(row['BRANCHNAME']) if not pd.isna(row['BRANCHNAME']) else None,
                pan_number=str(row['PANCARD']) if not pd.isna(row['PANCARD']) else None,
                # Wallets
                wallet_balance=0.0,
                earning_wallet=0.0,
                withdrawable_wallet=0.0,
                # KYC
                kyc_status='Pending',
                # Placement
                placement_status='Placed' if not pd.isna(row['POSITIONID']) else 'Unplaced'
            )
            
            db.add(new_user)
            imported += 1
            
            # Commit in batches
            if imported % 100 == 0:
                db.commit()
                print(f"   Imported {imported} users...")
                
        except Exception as e:
            error_msg = f"Row {idx + 2}: {user_id} - {str(e)}"
            errors.append(error_msg)
            print(f"   ❌ Error: {error_msg}")
    
    # Final commit
    db.commit()
    
    print(f"\n✅ Import Summary:")
    print(f"   Imported: {imported}")
    print(f"   Skipped: {skipped}")
    print(f"   Errors: {len(errors)}")
    
    if errors:
        print(f"\n❌ Errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"   {error}")
    
    return imported

def main():
    """Main execution"""
    print("=" * 80)
    print("USER UPLOAD FROM EXCEL - REPLACE EXISTING USERS")
    print("=" * 80)
    
    db = next(get_db())
    
    try:
        # Step 1: Get admin users to preserve
        admin_ids = get_admin_users(db)
        
        # Step 2: Delete non-admin users
        confirmation = input(f"\n⚠️  WARNING: This will delete {db.query(User).filter(~User.id.in_(admin_ids)).count()} non-admin users!\nType 'YES' to continue: ")
        if confirmation != 'YES':
            print("❌ Operation cancelled")
            return
        
        delete_non_admin_users(db, admin_ids)
        
        # Step 3: Import users from Excel
        imported = import_users_from_excel(db)
        
        # Step 4: Summary
        final_count = db.query(User).count()
        print(f"\n" + "=" * 80)
        print(f"✅ UPLOAD COMPLETE!")
        print(f"   Total users in system: {final_count}")
        print(f"   Admin users preserved: {len(admin_ids)}")
        print(f"   New users imported: {imported}")
        print("=" * 80)
        
        print("\n📊 Next Step: Trigger income calculations")
        print("   Run: python backend/scripts/trigger_all_incomes.py")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
