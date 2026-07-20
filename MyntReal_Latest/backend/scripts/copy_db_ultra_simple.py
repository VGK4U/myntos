#!/usr/bin/env python3
"""
Ultra Simple Database Copy - Development to Production
Uses raw SQL COPY commands for reliable transfer
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from datetime import datetime

DEV_URL = "postgresql://neondb_owner:npg_LYfk0Nre2IKo@ep-bitter-heart-adi4zlxw.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
PROD_URL = "postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

def main():
    print("\n" + "="*70)
    print("  DATABASE COPY - Development → Production")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Confirm
    print("⚠️  WARNING: This will REPLACE all production data!")
    response = input("\nType 'YES' to continue: ").strip()
    
    if response != 'YES':
        print("\n❌ Cancelled")
        sys.exit(0)
    
    print("\n🚀 Starting copy...\n")
    
    try:
        # Connect
        print("📡 Connecting to databases...")
        dev_conn = psycopg2.connect(DEV_URL)
        prod_conn = psycopg2.connect(PROD_URL)
        dev_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        prod_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print("✅ Connected\n")
        
        dev_cur = dev_conn.cursor()
        prod_cur = prod_conn.cursor()
        
        # Get all tables
        print("📋 Getting tables from development...")
        dev_cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = [row[0] for row in dev_cur.fetchall()]
        print(f"✅ Found {len(tables)} tables\n")
        
        # Drop all production tables
        print("🗑️  Dropping production tables...")
        for table in tables:
            # Validate table name (alphanumeric + underscore only)
            if table and isinstance(table, str) and table.replace('_', '').replace('-', '').isalnum():
                prod_cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
            else:
                print(f"   ⚠️  Skipped invalid table name: {table}")
        print("✅ Dropped\n")
        
        # Copy each table
        print(f"📦 Copying {len(tables)} tables:\n")
        
        for i, table in enumerate(tables, 1):
            try:
                # Validate table name before processing
                if not (table and isinstance(table, str) and table.replace('_', '').replace('-', '').isalnum()):
                    print(f"[{i}/{len(tables)}] ✗ {table}: Invalid table name")
                    continue
                
                # Get columns
                dev_cur.execute(f"""
                    SELECT column_name, data_type, character_maximum_length, 
                           column_default, is_nullable
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))
                
                columns = []
                for col in dev_cur.fetchall():
                    col_name = col[0]
                    col_type = col[1].upper()
                    
                    # Map common types
                    if col_type == 'CHARACTER VARYING':
                        if col[2]:
                            col_type = f'VARCHAR({col[2]})'
                        else:
                            col_type = 'VARCHAR'
                    elif col_type == 'INTEGER':
                        col_type = 'INTEGER'
                    elif col_type == 'BIGINT':
                        col_type = 'BIGINT'
                    elif col_type == 'TIMESTAMP WITHOUT TIME ZONE':
                        col_type = 'TIMESTAMP'
                    elif col_type == 'TIMESTAMP WITH TIME ZONE':
                        col_type = 'TIMESTAMPTZ'
                    elif col_type == 'BOOLEAN':
                        col_type = 'BOOLEAN'
                    elif col_type == 'TEXT':
                        col_type = 'TEXT'
                    elif col_type == 'NUMERIC':
                        col_type = 'NUMERIC'
                    elif col_type == 'DOUBLE PRECISION':
                        col_type = 'DOUBLE PRECISION'
                    elif col_type == 'DATE':
                        col_type = 'DATE'
                    
                    col_def = f'"{col_name}" {col_type}'
                    
                    # Add NOT NULL
                    if col[4] == 'NO':
                        col_def += ' NOT NULL'
                    
                    # Add DEFAULT
                    if col[3] and not col[3].startswith('nextval'):
                        col_def += f' DEFAULT {col[3]}'
                    
                    columns.append(col_def)
                
                # Create table
                create_sql = f'CREATE TABLE "{table}" ({", ".join(columns)});'
                prod_cur.execute(create_sql)
                
                # Get row count
                dev_cur.execute(f'SELECT COUNT(*) FROM "{table}";')
                count = dev_cur.fetchone()[0]
                
                # Copy data if exists
                if count > 0:
                    dev_cur.execute(f'SELECT * FROM "{table}";')
                    rows = dev_cur.fetchall()
                    
                    # Get column names for insert
                    dev_cur.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = %s
                        ORDER BY ordinal_position;
                    """, (table,))
                    col_names = [r[0] for r in dev_cur.fetchall()]
                    
                    # Insert data
                    placeholders = ','.join(['%s'] * len(col_names))
                    quoted_cols = ','.join([f'"{c}"' for c in col_names])
                    insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})'
                    
                    prod_cur.executemany(insert_sql, rows)
                    
                    print(f"[{i}/{len(tables)}] ✓ {table}: {count:,} rows")
                else:
                    print(f"[{i}/{len(tables)}] ✓ {table}: 0 rows")
                
            except Exception as e:
                print(f"[{i}/{len(tables)}] ✗ {table}: {str(e)[:80]}")
        
        print(f"\n✅ COPY COMPLETE!")
        print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📝 Next steps:")
        print("   1. Restart FastAPI Backend workflow")
        print("   2. Login as BEV180143")
        print("   3. Check earnings")
        
        dev_conn.close()
        prod_conn.close()
        
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
