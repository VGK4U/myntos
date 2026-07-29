import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
res = db.execute(text("""
    SELECT pid, state, wait_event_type, wait_event, query 
    FROM pg_stat_activity 
    WHERE state != 'idle' AND pid != pg_backend_pid();
"""))
print("Active queries:")
for row in res:
    print(row)
db.close()
