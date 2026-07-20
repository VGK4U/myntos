"""
User Import Script from Excel
Imports 896 users while preserving protected admin accounts
"""

import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from werkzeug.security import generate_password_hash

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Protected users that should NOT be deleted
PROTECTED_USERS = [
    'BEV182364369',  # RVZ ID
    'BEV182371007',  # Super Admin
    'BEV182371010',  # Finance Admin
    'BEV182322707',  # Admin
]

def excel_date_to_python(excel_date, excel_time=0):
    """Convert Excel date number to Python datetime"""
    # Excel epoch is 1899-12-30
    excel_epoch = datetime(1899, 12, 30)
    days = int(excel_date)
    seconds = int(excel_time * 86400)  # Convert fraction of day to seconds
    return excel_epoch + timedelta(days=days, seconds=seconds)

def get_package_amount(package_type):
    """Get package activation amount based on type"""
    package_amounts = {
        0: 0,
        1: 5000,    # Platinum
        2: 10000,   # Diamond
        3: 25000,   # Star
        4: 50000,   # Loyal
    }
    return package_amounts.get(int(package_type), 0)

def delete_non_protected_users(session):
    """FULL CLEAN: Delete ALL data from ALL tables except protected users"""
    # Use parameterized query instead of string formatting
    placeholders = ','.join([f':protected{i}' for i in range(len(PROTECTED_USERS))])
    params = {f'protected{i}': PROTECTED_USERS[i] for i in range(len(PROTECTED_USERS))}
    
    # Get count first
    result = session.execute(
        text(f"""
            SELECT COUNT(*) FROM "user" WHERE id NOT IN ({placeholders})
        """),
        params
    )
    count = result.scalar()
    
    print(f"\n🗑️  FULL CLEAN IMPORT: Deleting {count} non-protected users...")
    print("⚠️  This will DELETE ALL DATA from ALL tables for fresh start!")
    
    # Step 1: Get all tables with FK to user table
    print("\n   Step 1: Deleting from ALL related tables...")
    
    # Get ALL tables that reference user table automatically
    tables_query = session.execute(text("""
        SELECT DISTINCT tc.table_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND ccu.table_name = 'user'
            AND tc.table_name != 'user'
    """))
    
    tables_to_clear = [row[0] for row in tables_query.fetchall()]
    print(f"   Found {len(tables_to_clear)} tables with FK to user table")
    
    # Truncate all related tables
    for i, table in enumerate(tables_to_clear):
        try:
            # Validate table name (alphanumeric + underscore only)
            if table and isinstance(table, str) and table.replace('_', '').replace('-', '').isalnum():
                session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
                if (i+1) % 20 == 0:
                    print(f"      Cleared {i+1}/{len(tables_to_clear)} tables...")
            else:
                print(f"      ⚠️  Skipped invalid table name: {table}")
        except Exception as e:
            # Table might not exist or already empty - skip
            pass
    
    session.commit()
    print(f"✅ Cleared all related tables")
    
    # Step 2: Clear user self-references
    print("\n   Step 2: Clearing user self-references...")
    session.execute(text(f"""
        UPDATE "user" SET 
            ved_owner_id = NULL, 
            position_id = NULL, 
            referrer_id = NULL
    """))
    session.commit()
    
    # Step 3: Delete users
    print(f"\n   Step 3: Deleting {count} users...")
    # Reuse parameterized query
    placeholders = ','.join([f':protected{i}' for i in range(len(PROTECTED_USERS))])
    params = {f'protected{i}': PROTECTED_USERS[i] for i in range(len(PROTECTED_USERS))}
    session.execute(
        text(f"""
            DELETE FROM "user" WHERE id NOT IN ({placeholders})
        """),
        params
    )
    session.commit()
    
    print(f"✅ FULL CLEAN COMPLETE - Deleted {count} users and all related data")
    return count

def import_users_from_excel(excel_file):
    """Import users from Excel file"""
    session = Session()
    
    try:
        print("\n" + "="*80)
        print("IMPORTING USERS FROM EXCEL")
        print("="*80)
        
        # Step 1: Delete non-protected users
        deleted_count = delete_non_protected_users(session)
        
        # Step 2: Read Excel file
        print(f"\n📄 Reading Excel file: {excel_file}")
        df = pd.read_excel(excel_file)
        print(f"✅ Found {len(df)} users in Excel")
        
        # Step 3: Import users
        print(f"\n📥 Importing users...")
        imported = 0
        skipped = 0
        errors = 0
        
        for index, row in df.iterrows():
            try:
                user_id = str(row['MEMBERID'])
                
                # Skip if protected user
                if user_id in PROTECTED_USERS:
                    print(f"⏭️  Skipping protected user: {user_id}")
                    skipped += 1
                    continue
                
                # Parse name
                full_name = str(row['NAME']).strip()
                name_parts = full_name.split(' ', 1)
                first_name = name_parts[0] if len(name_parts) > 0 else full_name
                last_name = name_parts[1] if len(name_parts) > 1 else ''
                
                # Hash password
                password = str(row['PASSWORD'])
                password_hash = generate_password_hash(password)
                
                # Parse dates
                created_at = excel_date_to_python(row['DOJ'], row.get('TIME', 0))
                
                # Package info
                package_type = int(row.get('PACKAGE TYPE', 0))
                is_activated = package_type > 0
                activation_amount = get_package_amount(package_type)
                
                # Status
                user_status = str(row.get('USER STATUS', 'Inactive')).strip()
                status = 'Active' if user_status.lower() == 'active' else 'Inactive'
                
                # Sponsor and Position
                sponsor_id = str(row['SPONSORID']) if pd.notna(row['SPONSORID']) else None
                position_id = str(row['POSITIONID']) if pd.notna(row['POSITIONID']) else None
                position = str(row.get('POSITION', '')).strip().capitalize() if pd.notna(row.get('POSITION')) else None
                
                # Special handling for BEV1800001
                if user_id == 'BEV1800001':
                    sponsor_id = 'BEV182371007'  # Super Admin
                    position_id = 'BEV182322707'  # Admin
                    position = 'Left'
                
                # Bank details
                account_number = str(int(row['ACCOUNTNO'])) if pd.notna(row['ACCOUNTNO']) and row['ACCOUNTNO'] != '' else None
                bank_name = str(row['BANKNAME']) if pd.notna(row['BANKNAME']) else None
                ifsc_code = str(row['IFSC']) if pd.notna(row['IFSC']) else None
                branch_name = str(row['BRANCHNAME']) if pd.notna(row['BRANCHNAME']) else None
                pan_card = str(row['PANCARD']) if pd.notna(row['PANCARD']) else None
                
                # Email and phone
                email = str(row['EMAILID']) if pd.notna(row['EMAILID']) and row['EMAILID'] != '' else None
                phone = str(row['PHONENO']) if pd.notna(row['PHONENO']) else None
                
                # Insert user
                session.execute(text("""
                    INSERT INTO "user" (
                        id, first_name, last_name, phone_number, email, password_hash,
                        referrer_id, position_id, position, role, status, 
                        package_id, package_activated, activation_date, activation_amount,
                        earning_wallet, withdrawable_wallet, total_earnings, total_withdrawal,
                        left_team_count, right_team_count, left_team_active_count, right_team_active_count,
                        matching_count, total_direct_referrals, active_direct_referrals,
                        account_number, bank_name, ifsc_code, branch_name, pan_card,
                        ved_owner_id, is_ved, created_at
                    ) VALUES (
                        :id, :first_name, :last_name, :phone_number, :email, :password_hash,
                        :referrer_id, :position_id, :position, :role, :status,
                        :package_id, :package_activated, :activation_date, :activation_amount,
                        0, 0, 0, 0,
                        0, 0, 0, 0,
                        0, 0, 0,
                        :account_number, :bank_name, :ifsc_code, :branch_name, :pan_card,
                        NULL, FALSE, :created_at
                    )
                """), {
                    'id': user_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone,
                    'email': email,
                    'password_hash': password_hash,
                    'referrer_id': sponsor_id,
                    'position_id': position_id,
                    'position': position,
                    'role': 'USER',
                    'status': status,
                    'package_id': package_type,
                    'package_activated': is_activated,
                    'activation_date': created_at if is_activated else None,
                    'activation_amount': activation_amount if is_activated else 0,
                    'account_number': account_number,
                    'bank_name': bank_name,
                    'ifsc_code': ifsc_code,
                    'branch_name': branch_name,
                    'pan_card': pan_card,
                    'created_at': created_at
                })
                
                imported += 1
                if imported % 100 == 0:
                    session.commit()
                    print(f"   ✅ Imported {imported} users...")
                
            except Exception as e:
                errors += 1
                print(f"   ❌ Error importing {row.get('MEMBERID')}: {str(e)[:100]}")
                continue
        
        # Final commit
        session.commit()
        
        print(f"\n" + "="*80)
        print(f"✅ IMPORT COMPLETE!")
        print(f"   • Deleted: {deleted_count} users")
        print(f"   • Imported: {imported} users")
        print(f"   • Skipped: {skipped} users (protected)")
        print(f"   • Errors: {errors} users")
        print("="*80)
        
        return imported, errors
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0
    finally:
        session.close()

def recalculate_team_counts(session):
    """Recalculate team counts and Ved hierarchy"""
    print("\n" + "="*80)
    print("RECALCULATING TEAM STRUCTURE")
    print("="*80)
    
    # Reset all counts first
    print("\n🔄 Resetting team counts...")
    session.execute(text("""
        UPDATE "user" SET 
            left_team_count = 0,
            right_team_count = 0,
            left_team_active_count = 0,
            right_team_active_count = 0,
            matching_count = 0,
            total_direct_referrals = 0,
            active_direct_referrals = 0,
            ved_owner_id = NULL,
            is_ved = FALSE
    """))
    session.commit()
    print("✅ Counts reset")
    
    # Recalculate direct referrals
    print("\n🔄 Calculating direct referrals...")
    session.execute(text("""
        UPDATE "user" u SET
            total_direct_referrals = (
                SELECT COUNT(*) FROM "user" ref WHERE ref.referrer_id = u.id
            ),
            active_direct_referrals = (
                SELECT COUNT(*) FROM "user" ref 
                WHERE ref.referrer_id = u.id AND ref.package_activated = TRUE
            )
    """))
    session.commit()
    print("✅ Direct referrals calculated")
    
    # Calculate team counts (recursive would be better but using iterative approach)
    print("\n🔄 Calculating team counts (this may take a while)...")
    
    # Get all users ordered by depth (root first)
    users = session.execute(text("""
        WITH RECURSIVE team_tree AS (
            SELECT id, position_id, position, package_activated, 0 as depth
            FROM "user"
            WHERE position_id IS NULL OR position_id NOT IN (SELECT id FROM "user")
            
            UNION ALL
            
            SELECT u.id, u.position_id, u.position, u.package_activated, tt.depth + 1
            FROM "user" u
            INNER JOIN team_tree tt ON u.position_id = tt.id
            WHERE tt.depth < 50
        )
        SELECT id, position_id, position, package_activated, depth
        FROM team_tree
        ORDER BY depth DESC
    """)).fetchall()
    
    # Update counts from bottom to top
    for user in users:
        user_id = user[0]
        
        # Calculate left team
        left_count = session.execute(text("""
            WITH RECURSIVE downline AS (
                SELECT id, package_activated
                FROM "user"
                WHERE position_id = :user_id AND position = 'Left'
                
                UNION ALL
                
                SELECT u.id, u.package_activated
                FROM "user" u
                INNER JOIN downline d ON u.position_id = d.id
            )
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN package_activated = TRUE THEN 1 ELSE 0 END) as active
            FROM downline
        """), {'user_id': user_id}).fetchone()
        
        # Calculate right team
        right_count = session.execute(text("""
            WITH RECURSIVE downline AS (
                SELECT id, package_activated
                FROM "user"
                WHERE position_id = :user_id AND position = 'Right'
                
                UNION ALL
                
                SELECT u.id, u.package_activated
                FROM "user" u
                INNER JOIN downline d ON u.position_id = d.id
            )
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN package_activated = TRUE THEN 1 ELSE 0 END) as active
            FROM downline
        """), {'user_id': user_id}).fetchone()
        
        # Update user
        session.execute(text("""
            UPDATE "user" SET
                left_team_count = :left_total,
                left_team_active_count = :left_active,
                right_team_count = :right_total,
                right_team_active_count = :right_active,
                matching_count = LEAST(:left_active, :right_active)
            WHERE id = :user_id
        """), {
            'user_id': user_id,
            'left_total': left_count[0] or 0,
            'left_active': left_count[1] or 0,
            'right_total': right_count[0] or 0,
            'right_active': right_count[1] or 0
        })
    
    session.commit()
    print("✅ Team counts calculated")
    
    # Calculate Ved ownership
    print("\n🔄 Calculating Ved ownership...")
    session.execute(text("""
        UPDATE "user" u SET
            ved_owner_id = (
                WITH RECURSIVE ved_chain AS (
                    SELECT referrer_id, 0 as level
                    FROM "user" 
                    WHERE id = u.id AND referrer_id IS NOT NULL
                    
                    UNION ALL
                    
                    SELECT ur.referrer_id, vc.level + 1
                    FROM "user" ur
                    INNER JOIN ved_chain vc ON ur.id = vc.referrer_id
                    WHERE ur.referrer_id IS NOT NULL AND vc.level < 50
                )
                SELECT referrer_id FROM ved_chain
                WHERE referrer_id IN (
                    SELECT id FROM "user" WHERE total_direct_referrals >= 5
                )
                ORDER BY level ASC
                LIMIT 1
            )
    """))
    
    # Mark Ved members
    session.execute(text("""
        UPDATE "user" SET is_ved = TRUE
        WHERE total_direct_referrals >= 5
    """))
    
    session.commit()
    print("✅ Ved ownership calculated")
    
    print("\n" + "="*80)
    print("✅ RECALCULATION COMPLETE!")
    print("="*80)

if __name__ == "__main__":
    excel_file = "../attached_assets/Users5.20251008205014699_1760278834616.xlsx"
    
    # Import users
    imported, errors = import_users_from_excel(excel_file)
    
    # Recalculate if import successful
    if imported > 0:
        session = Session()
        try:
            recalculate_team_counts(session)
        finally:
            session.close()
    
    print("\n✅ ALL DONE!")
