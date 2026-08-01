#!/usr/bin/env python3
"""
Standalone Sandbox Seeder for Ganesh Seva Community Services
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, "/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend")

from app.core.database import SessionLocal
from app.services.sandbox_seeder import seed_sandbox_data

def run_seeder():
    db = SessionLocal()
    try:
        print("Starting sandbox community data seeding...")
        result = seed_sandbox_data(db)
        print(f"Success: {result['message']}")
        print(f"Data: {result['data']}")
        return True
    except Exception as e:
        import traceback
        print(f"Seeding failed: {e}")
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run_seeder()
    sys.exit(0 if success else 1)
