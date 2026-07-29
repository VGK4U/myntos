import sys
import os
import jwt
from datetime import datetime, timedelta
sys.path.append(r"C:\Desktop\VGK4U\MyntReal_Latest\backend")
from app.main import app
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from fastapi.testclient import TestClient

db = SessionLocal()
staff = db.query(StaffEmployee).filter_by(emp_code="MN10003").first()

token = jwt.encode(
    {"sub": str(staff.id), "exp": datetime.utcnow() + timedelta(days=1), "user_type": "staff", "role": getattr(staff.role, 'name', 'EA') if hasattr(staff, 'role') else 'EA'}, 
    os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"), 
    algorithm="HS256"
)

client = TestClient(app)
response = client.get("/api/v1/crm/lead-analytics", headers={"Authorization": f"Bearer {token}"})
if response.status_code == 500:
    print(response.text)
else:
    print("SUCCESS", response.status_code)
