import sys
import os
import jwt
from datetime import datetime, timedelta
sys.path.append(r"C:\Desktop\VGK4U\MyntReal_Latest\backend")

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.core.config import settings

client = TestClient(app)

def run_stress_test():
    print("[AUDIT] Generating Master Admin JWT Token...")
    db = SessionLocal()
    # Find a super admin or just any staff
    staff = db.query(StaffEmployee).filter(StaffEmployee.role_id == 1).first()
    if not staff:
        print("ERROR: No staff found in DB to impersonate.")
        db.close()
        return
        
    role_name = getattr(staff.role, 'name', 'EA') if hasattr(staff, 'role') else 'EA'
    staff_id_str = str(staff.id)
    
    db.close() # CRITICAL: Close the session to release any locks before starting TestClient
        
    token_data = {
        "sub": staff_id_str, 
        "exp": datetime.utcnow() + timedelta(days=1), 
        "user_type": "staff", 
        "role": role_name
    }
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    print("[AUDIT] Fetching OpenAPI specification to map all endpoints...")
    response = client.get("/openapi.json")
    if response.status_code != 200:
        print("ERROR: Could not fetch OpenAPI spec.")
        return
        
    openapi = response.json()
    paths = openapi.get("paths", {})
    
    get_endpoints = []
    for path, methods in paths.items():
        if "get" in methods:
            # Skip endpoints that obviously require path parameters (e.g. /leads/{id})
            if "{" not in path:
                get_endpoints.append(path)
                
    print(f"[AUDIT] Discovered {len(get_endpoints)} GET endpoints without path parameters.")
    print("[AUDIT] Firing requests to all endpoints...")
    
    failed_endpoints = []
    
    for i, path in enumerate(get_endpoints, 1):
        print(f"Testing [{i}/{len(get_endpoints)}] {path} ...", flush=True)
        try:
            res = client.get(path, headers=headers, timeout=5)
            if res.status_code == 500:
                failed_endpoints.append((path, "500 Internal Server Error", res.text[:200]))
            elif res.status_code == 422:
                # Validation error (missing query params), this is fine.
                pass
            print(f"[{i}/{len(get_endpoints)}] {path} -> {res.status_code}", flush=True)
        except Exception as e:
            failed_endpoints.append((path, "CRASH OR TIMEOUT", str(e)[:200]))
            print(f"[{i}/{len(get_endpoints)}] {path} -> CRASH OR TIMEOUT", flush=True)
            
    print("\n--- STRESS TEST RESULTS ---")
    if failed_endpoints:
        print(f"❌ FAILURE: {len(failed_endpoints)} endpoints threw 500 Server Errors or Crashed!")
        for path, status, err in failed_endpoints:
            print(f"\n[FAIL] {path}")
            print(f"       Reason: {status}")
            print(f"       Details: {err}")
    else:
        print("✅ SUCCESS: No 500 errors triggered during the endpoint stress test.")
        
if __name__ == "__main__":
    run_stress_test()
