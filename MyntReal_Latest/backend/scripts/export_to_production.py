#!/usr/bin/env python3
"""
Export Development Database to Production
Exports all critical data tables for production deployment
"""
import os
import sys
sys.path.insert(0, '/home/runner/workspace/backend')

from app.core.database import SessionLocal
from sqlalchemy import text
import json
from datetime import datetime

def export_data():
    """Export all development data to SQL file"""
    db = SessionLocal()
    
    print("🔄 Exporting Development Database to Production Format...")
    print("=" * 60)
    
    # Tables to export in correct order (respecting foreign keys)
    tables_order = [
        'system_checkpoints',
        'user',
        'placement',
        'direct_award_tier',
        'matching_award_tier', 
        'dynamic_bonanza_tier',
        'user_award_progress',
        'user_matching_award_progress',
        'dynamic_bonanza_history',
        'income',
        'transaction',
        'withdrawal'
    ]
    
    export_file = '/tmp/production_data_export.sql'
    
    with open(export_file, 'w') as f:
        f.write("-- MNR Production Database Import\n")
        f.write(f"-- Generated: {datetime.now()}\n")
        f.write("-- IMPORTANT: Run this on PRODUCTION database only!\n\n")
        f.write("BEGIN;\n\n")
        
        for table in tables_order:
            try:
                # Get row count
                count_result = db.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = count_result.scalar()
                
                if count == 0:
                    print(f"⏭️  {table}: 0 rows (skipping)")
                    continue
                
                print(f"✅ Exporting {table}: {count} rows")
                
                # Export data using COPY for efficiency
                f.write(f"-- Table: {table} ({count} rows)\n")
                
                # Get column names
                cols_result = db.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                columns = [row[0] for row in cols_result]
                
                # Get all data
                data_result = db.execute(text(f'SELECT * FROM "{table}"'))
                rows = data_result.fetchall()
                
                if rows:
                    # Generate INSERT statements
                    col_list = ', '.join([f'"{col}"' for col in columns])
                    
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, bool):
                                values.append('TRUE' if val else 'FALSE')
                            elif isinstance(val, datetime):
                                values.append(f"'{val.isoformat()}'")
                            else:
                                # Escape single quotes
                                escaped = str(val).replace("'", "''")
                                values.append(f"'{escaped}'")
                        
                        value_list = ', '.join(values)
                        f.write(f'INSERT INTO "{table}" ({col_list}) VALUES ({value_list});\n')
                
                f.write(f"\n")
                
            except Exception as e:
                print(f"⚠️  Error exporting {table}: {e}")
                continue
        
        f.write("COMMIT;\n")
    
    db.close()
    
    print("\n" + "=" * 60)
    print(f"✅ Export complete: {export_file}")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Download this file from Replit")
    print("2. Go to your Production Database pane")
    print("3. Execute this SQL file")
    print("\nOR use the production import script (recommended)")
    
    return export_file

if __name__ == "__main__":
    export_data()
