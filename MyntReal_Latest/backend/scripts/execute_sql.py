import sys
import os

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal, engine

sql_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations", "add_68_missing_columns_20260722.sql")

with open(sql_file, "r") as f:
    sql = f.read()

print("Executing SQL...")
with SessionLocal() as db:
    # We can execute the raw SQL string
    try:
        db.execute(text(sql))
        db.commit()
        print("SQL executed successfully.")
    except Exception as e:
        print(f"Error executing SQL: {e}")
        db.rollback()
