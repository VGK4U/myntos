import sys
import os
sys.path.append(r"C:\Desktop\VGK4U\MyntReal_Latest\backend")

from sqlalchemy import inspect
from app.core.database import engine
from app.models import base
from app.models import *

def audit_schema():
    print("[AUDIT] Starting Database Schema Introspection...")
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    
    missing_tables = []
    missing_columns = []
    
    for mapper in base.Base.registry.mappers:
        model = mapper.class_
        table_name = model.__tablename__
        
        if table_name not in db_tables:
            missing_tables.append(table_name)
            continue
            
        db_columns = [col['name'] for col in inspector.get_columns(table_name)]
        model_columns = [col.name for col in mapper.columns]
        
        for m_col in model_columns:
            if m_col not in db_columns:
                missing_columns.append(f"{table_name}.{m_col}")
                
    print("\n--- AUDIT RESULTS ---")
    print(f"Tables in Model missing in DB: {len(missing_tables)}")
    for t in missing_tables:
        print(f" - {t}")
        
    print(f"\nColumns in Model missing in DB: {len(missing_columns)}")
    for c in missing_columns:
        print(f" - {c}")
        
    if not missing_tables and not missing_columns:
        print("\nSUCCESS: All SQLAlchemy models perfectly match the live database schema!")
    else:
        print("\nFAILURE: Schema mismatches found. These WILL cause 500 errors if queried.")

if __name__ == "__main__":
    audit_schema()
