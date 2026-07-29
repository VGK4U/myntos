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
staff = db.query(StaffEmployee).filter_by(emp_code="MR10001").first()

token = jwt.encode(
    {"sub": str(staff.id), "exp": datetime.utcnow() + timedelta(days=1), "user_type": "staff", "role": staff.role}, 
    os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"), 
    algorithm="HS256"
)

client = TestClient(app)
response = client.get("/api/v1/crm/master-leads?category=solar", headers={"Authorization": f"Bearer {token}"})
print("STATUS:", response.status_code)
if response.status_code != 500:
    data = response.json()
    print("SUCCESS! Got leads:", len(data.get('data', [])))
else:
    print(response.text)
