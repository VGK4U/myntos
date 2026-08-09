"""
Phase 2L.3 Har Ghar Solar Dedicated Ad Set & Single-Ad Execution Script
Executes clean, dedicated advertising path creation for Har Ghar Solar under Campaign 120254919777680348.
"""

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.services.meta_har_ghar_solar_creation_service import execute_har_ghar_solar_dedicated_creation

if __name__ == "__main__":
    db = SessionLocal()
    print("============================================================")
    print("MYNT OS — PHASE 2L.3 HAR GHAR SOLAR DEDICATED EXECUTION")
    print("============================================================\n")

    res = execute_har_ghar_solar_dedicated_creation(db, company_id=1, language="en_te")
    print(json.dumps(res, indent=2))

    db.close()
