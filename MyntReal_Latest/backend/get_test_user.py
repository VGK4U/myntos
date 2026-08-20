import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

# Append backend to path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.models.user import User

DATABASE_URL = "postgresql://postgres:MyntRealAdmin2026!@myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com:5432/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Find a regular member
user = db.query(User).filter(User.user_type == 'Member', User.account_status == 'Active').first()
if user:
    # Reset password to TestPass123!
    new_password = "TestPass123!"
    user.password = generate_password_hash(new_password)
    db.commit()
    print(f"--- SUCCESS ---")
    print(f"Username (MNR ID): {user.id}")
    print(f"Password: {new_password}")
else:
    print("No active members found.")
db.close()
