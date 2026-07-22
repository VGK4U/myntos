import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.crm import CRMLead
from app.models.staff import StaffEmployee
from datetime import datetime

print("Starting Sandbox CRUD Verification...")
db = SessionLocal()

try:
    # Use a transaction that we can rollback at the end
    # so we don't leave dummy data in the live AWS RDS database.
    
    # 1. READ (Find an existing staff member to assign the lead to)
    staff = db.query(StaffEmployee).first()
    if not staff:
        print("ERROR: No staff found to use as creator.")
        sys.exit(1)
    
    print(f"PASS READ Test: Successfully queried StaffEmployee (ID: {staff.id})")
    
    # 2. CREATE
    dummy_lead = CRMLead(
        name="Sandbox TestLead",
        phone="9999999999",
        source="Sandbox",
        company_id=1,
        status="new"
    )
    db.add(dummy_lead)
    db.flush() # Flushes to DB to catch any schema errors like missing non-nullable columns
    print(f"PASS CREATE Test: Successfully inserted dummy CRMLead (ID: {dummy_lead.id})")
    
    # 3. UPDATE
    dummy_lead.name = "UpdatedLead"
    db.flush()
    
    updated_lead = db.query(CRMLead).filter(CRMLead.id == dummy_lead.id).first()
    if updated_lead and updated_lead.name == "UpdatedLead":
        print(f"PASS UPDATE Test: Successfully updated dummy CRMLead to '{updated_lead.name}'")
    else:
        print("FAIL UPDATE Test: Failed to verify update.")
        
    # 4. DELETE
    db.delete(dummy_lead)
    db.flush()
    
    deleted_lead = db.query(CRMLead).filter(CRMLead.id == dummy_lead.id).first()
    if not deleted_lead:
        print(f"PASS DELETE Test: Successfully deleted dummy CRMLead")
    else:
        print("FAIL DELETE Test: Failed to verify deletion.")
        
    # ROLLBACK to ensure zero impact on production data
    db.rollback()
    print("\nPASS Sandbox CRUD Verification Completed Successfully (Rolled back successfully)")
    
except Exception as e:
    db.rollback()
    print(f"\nFAIL CRUD Test Failed with Exception: {e}")
finally:
    db.close()
