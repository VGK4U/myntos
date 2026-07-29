import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app
from fastapi.testclient import TestClient

print("Creating TestClient...")
client = TestClient(app)
print("Client created. Testing /health...")
res = client.get("/health")
print("Response:", res.status_code)
