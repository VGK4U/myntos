import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.models.staff import StaffEmployee

DATABASE_URL = "postgresql://postgres:MyntRealAdmin2026!@myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com:5432/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

staff = db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()
if staff:
    staff.password_hash = generate_password_hash("TestPass123!")
    db.commit()
    print("SUCCESS: Reset MR10001 password")
else:
    print("FAILED: MR10001 not found")
db.close()
