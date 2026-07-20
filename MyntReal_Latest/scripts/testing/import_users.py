import pandas as pd
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Read the Excel file
df = pd.read_excel('attached_assets/Users5_1759900353006.xlsx')

# Convert Excel date to Python date
def excel_date_to_python(excel_date):
    if pd.isna(excel_date):
        return datetime.now()
    base_date = datetime(1899, 12, 30)
    return base_date + timedelta(days=int(excel_date))

print(f"Importing {len(df)} users...")

# Generate SQL statements
sql_statements = []

for idx, row in df.iterrows():
    user_id = str(row['MEMBERID']).strip()
    name = str(row['NAME']).strip() if pd.notna(row['NAME']) else 'User'
    name = name.replace("'", "''")  # Escape single quotes
    
    password = str(row['PASSWORD']).strip() if pd.notna(row['PASSWORD']) else '123456'
    phone = str(row['PHONENO']).strip() if pd.notna(row['PHONENO']) else ''
    email = str(row['EMAILID']).strip() if pd.notna(row['EMAILID']) else f"{user_id.lower()}@system.generated"
    sponsor_id = str(row['SPONSORID']).strip() if pd.notna(row['SPONSORID']) else None
    position_id = str(row['POSITIONID']).strip() if pd.notna(row['POSITIONID']) else None
    position = str(row['POSITION']).strip().upper() if pd.notna(row['POSITION']) else 'LEFT'
    user_status = str(row['USER STATUS']).strip() if pd.notna(row['USER STATUS']) else 'Inactive'
    coupon_status = str(row['COUPON / PACKAGE STATUS']).strip() if pd.notna(row['COUPON / PACKAGE STATUS']) else 'IN ACTIVE'
    
    # Convert status
    status = 'Active' if user_status.lower() == 'active' else 'Inactive'
    coupon_status_clean = 'Activated' if coupon_status.upper() == 'ACTIVATED' else 'Eligible'
    
    # Get registration date
    reg_date = excel_date_to_python(row['DOJ'])
    
    # Hash password
    password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    # User type
    user_type = 'User'
    
    # Progress indicator
    if idx % 100 == 0:
        print(f"Processing user {idx+1}/{len(df)}: {user_id}", file=sys.stderr)
    
    # User INSERT statement
    sponsor_sql = f"'{sponsor_id}'" if sponsor_id else 'NULL'
    user_sql = f"""INSERT INTO "user" (id, name, email, password, user_type, referrer_id, registration_date, wallet_balance, upgrade_wallet_balance, kyc_status, coupon_status, placement_status)
VALUES ('{user_id}', '{name}', '{email}', '{password_hash}', '{user_type}', {sponsor_sql}, '{reg_date.strftime('%Y-%m-%d %H:%M:%S')}', 0.0, 0.0, 'Pending', '{coupon_status_clean}', '{status}')
ON CONFLICT (id) DO UPDATE SET password = EXCLUDED.password, name = EXCLUDED.name;"""
    
    sql_statements.append(user_sql)
    
    # Placement INSERT statement
    if position_id and position:
        placement_sql = f"""INSERT INTO placement (user_id, parent_id, position, placement_date)
VALUES ('{user_id}', '{position_id}', '{position}', '{reg_date.strftime('%Y-%m-%d %H:%M:%S')}')
ON CONFLICT (user_id) DO NOTHING;"""
        sql_statements.append(placement_sql)

# Write to SQL file
with open('import_users.sql', 'w') as f:
    f.write("-- SQL Script to Import Users\n")
    f.write(f"-- Total users: {len(df)}\n")
    f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write('\n\n'.join(sql_statements))

print(f"\n✅ SQL script generated: import_users.sql")
print(f"Total users to import: {len(df)}")
print(f"Total SQL statements: {len(sql_statements)}")
