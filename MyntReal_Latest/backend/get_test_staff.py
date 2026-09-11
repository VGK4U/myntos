import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.models.staff import StaffEmployee

import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
DATABASE_URL = os.environ.get('PROD_DATABASE_URL') or os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("Database URL environment variable is not set")
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
