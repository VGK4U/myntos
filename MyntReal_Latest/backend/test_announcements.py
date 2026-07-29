import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
import jwt
from datetime import datetime, timedelta, UTC
from app.core.config import settings

print("Starting client...")
client = TestClient(app)

response = client.get("/api/v1/feedback/public/announcements")
print("Response status:", response.status_code)
if response.status_code != 200:
    print(response.json())
else:
    print("SUCCESS!")
