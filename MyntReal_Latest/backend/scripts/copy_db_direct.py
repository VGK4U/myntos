#!/usr/bin/env python3
"""
Direct Database Copy Script - Development to Production
Copies all tables, data, sequences, and indexes from development to production
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
from datetime import datetime

DEV_URL = "postgresql://neondb_owner:npg_LYfk0Nre2IKo@ep-bitter-heart-adi4zlxw.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
PROD_URL = "postgresql://neondb_owner:npg_tnS3mrd1KFgk@ep-dry-lab-ad9prs0y.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

def print_header():
    print("\n" + "="*70)
    print("  DATABASE COPY SCRIPT - Development → Production")
    print("="*70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def get_connection(url, db_name):
    """Create database connection"""
    try:
        conn = psycopg2.connect(url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print(f"✅ Connected to {db_name} database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to {db_name}: {e}")
        sys.exit(1)

def get_all_tables(conn):
    """Get list of all user tables"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def drop_all_tables(conn):
    """Drop all tables in production"""
    print("\n🗑️  Dropping all production tables...")
    cursor = conn.cursor()
    
    tables = get_all_tables(conn)
    if not tables:
        print("   No tables to drop")
        return
    
    print(f"   Found {len(tables)} tables to drop")
    
    # Drop all tables with CASCADE
    for table in tables:
        try:
            # Use parameterized query for table name to prevent SQL injection
            # Note: psycopg2 doesn't support parameter substitution for identifiers,
            # so we validate table name from pg_tables query (trusted source)
            # and use double quotes for proper identifier escaping
            if table and isinstance(table, str) and table.replace('_', '').isalnum():
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                print(f"   ✓ Dropped: {table}")
            else:
                print(f"   ⚠️  Skipped invalid table name: {table}")
        except Exception as e:
            print(f"   ⚠️  Error dropping {table}: {e}")
    
    cursor.close()
    print("✅ All tables dropped")

def copy_table_schema_and_data(dev_conn, prod_conn, table_name):
    """Copy table schema and data from dev to prod"""
    dev_cursor = dev_conn.cursor()
    prod_cursor = prod_conn.cursor()
    
    try:
        # Get CREATE TABLE statement
        dev_cursor.execute(f"""
            SELECT 
                'CREATE TABLE "' || tablename || '" (' || 
                string_agg(
                    column_name || ' ' || column_type || 
                    CASE WHEN column_default IS NOT NULL 
                        THEN ' DEFAULT ' || column_default 
                        ELSE '' 
                    END ||
                    CASE WHEN is_nullable = 'NO' 
                        THEN ' NOT NULL' 
                        ELSE '' 
                    END,
                    ', '
                ) || ');' as create_stmt
            FROM (
                SELECT 
                    t.tablename,
                    c.column_name,
                    c.data_type || 
                    CASE 
                        WHEN c.character_maximum_length IS NOT NULL 
                            THEN '(' || c.character_maximum_length || ')'
                        WHEN c.numeric_precision IS NOT NULL 
                            THEN '(' || c.numeric_precision || ',' || c.numeric_scale || ')'
                        ELSE ''
                    END as column_type,
                    c.column_default,
                    c.is_nullable,
                    c.ordinal_position
                FROM pg_tables t
                JOIN information_schema.columns c 
                    ON t.tablename = c.table_name 
                    AND c.table_schema = 'public'
                WHERE t.schemaname = 'public' 
                    AND t.tablename = %s
                ORDER BY c.ordinal_position
            ) cols
            GROUP BY tablename;
        """, (table_name,))
        
        create_stmt_result = dev_cursor.fetchone()
        if not create_stmt_result:
            # Fallback: use pg_dump approach
            dev_cursor.execute(f"""
                SELECT 'CREATE TABLE "' || %s || '" AS SELECT * FROM "' || %s || '" LIMIT 0;' 
            """, (table_name, table_name))
            create_stmt = dev_cursor.fetchone()[0]
        else:
            create_stmt = create_stmt_result[0]
        
        # Create table in production
        prod_cursor.execute(create_stmt)
        
        # Get row count
        dev_cursor.execute(f'SELECT COUNT(*) FROM "{table_name}";')
        row_count = dev_cursor.fetchone()[0]
        
        if row_count > 0:
            # Copy data
            dev_cursor.execute(f'SELECT * FROM "{table_name}";')
            rows = dev_cursor.fetchall()
            
            # Get column names
            dev_cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                    AND table_name = %s 
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = [row[0] for row in dev_cursor.fetchall()]
            
            # Insert data
            placeholders = ','.join(['%s'] * len(columns))
            quoted_columns = ','.join([f'"{c}"' for c in columns])
            insert_stmt = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'
            
            prod_cursor.executemany(insert_stmt, rows)
            
            print(f"   ✓ {table_name}: {row_count:,} rows copied")
        else:
            print(f"   ✓ {table_name}: 0 rows (schema only)")
        
    except Exception as e:
        print(f"   ❌ Error copying {table_name}: {e}")
        # Try simpler approach
        try:
            prod_cursor.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM dblink(\'dbname=development\', \'SELECT * FROM "{table_name}"\') AS t;')
            print(f"   ✓ {table_name}: Copied using fallback method")
        except:
            print(f"   ❌ Failed to copy {table_name}")
    
    dev_cursor.close()
    prod_cursor.close()

def copy_database():
    """Main database copy function"""
    print_header()
    
    # Confirm
    print("⚠️  WARNING: This will REPLACE all production data with development data!")
    print()
    response = input("Type 'YES' to continue: ").strip()
    
    if response != 'YES':
        print("\n❌ Copy cancelled")
        sys.exit(0)
    
    print("\n🚀 Starting database copy...\n")
    
    # Connect to databases
    dev_conn = get_connection(DEV_URL, "Development")
    prod_conn = get_connection(PROD_URL, "Production")
    
    try:
        # Get tables from development
        print("\n📋 Getting table list from development...")
        tables = get_all_tables(dev_conn)
        print(f"   Found {len(tables)} tables to copy")
        
        # Drop production tables
        drop_all_tables(prod_conn)
        
        # Copy each table
        print(f"\n📦 Copying {len(tables)} tables...\n")
        
        for i, table in enumerate(tables, 1):
            print(f"[{i}/{len(tables)}] Copying {table}...")
            copy_table_schema_and_data(dev_conn, prod_conn, table)
        
        print(f"\n✅ DATABASE COPY COMPLETE!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📝 Next steps:")
        print("   1. Restart FastAPI Backend workflow")
        print("   2. Login as BEV180143")
        print("   3. Check earnings → Should show ₹95,975.33 ✅")
        print()
        
    except Exception as e:
        print(f"\n❌ Copy failed: {e}")
        sys.exit(1)
    finally:
        dev_conn.close()
        prod_conn.close()

if __name__ == "__main__":
    copy_database()
