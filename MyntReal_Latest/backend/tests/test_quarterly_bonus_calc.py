from datetime import datetime, date
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Monkeypatch JSONB and TSVECTOR compile for SQLite test engine
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
SQLiteTypeCompiler.visit_TSVECTOR = lambda self, type_, **kw: "TEXT"

# Import models & schemas
from app.models import Base
from app.models.staff import StaffEmployee, StaffDepartment, StaffRole
from app.models.staff_accounts import AssociatedCompany
from app.models.signup_category import SignupCategory
from app.models.staff_bonus_config import StaffQuarterlyBonusConfig
from app.models.staff_kra import StaffKRADailyInstance
from app.models.staff_attendance import StaffActivityTimeLog
from app.models.crm import CRMLead

# Import FastAPI main app
from app.main import app
from app.core.database import get_db

# Create a temporary file-based SQLite database for testing to allow shared access across FastAPI client connection threads
import os
if os.path.exists("test_temp.db"):
    try:
        os.remove("test_temp.db")
    except Exception:
        pass

engine = create_engine("sqlite:///test_temp.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency in FastAPI app
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_db():
    # Remove duplicate index names for SQLite global namespace
    seen_indexes = set()
    for table in Base.metadata.tables.values():
        indexes_to_remove = []
        for idx in table.indexes:
            if idx.name in seen_indexes:
                indexes_to_remove.append(idx)
            else:
                seen_indexes.add(idx.name)
        for idx in indexes_to_remove:
            table.indexes.remove(idx)

    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed Department and Role
    dept = StaffDepartment(id=1, name="Sales Department", is_active=True)
    role = StaffRole(id=1, role_code="sales_agent", role_name="Sales Agent", hierarchy_level=1, is_active=True)
    comp = AssociatedCompany(id=1, company_code="MYNT", company_name="Mynt Company")
    db.add_all([dept, role, comp])
    db.commit()

    cat = SignupCategory(id=1, company_id=1, name="Solar", slug="solar")
    db.add(cat)
    db.commit()

    # Seed Default Employees
    emp1 = StaffEmployee(
        id=1,
        emp_code="MR10016",
        full_name="Yaswanth Kumar Appalabattula",
        department_id=1,
        role_id=1,
        is_quarterly_bonus_eligible=True,
        status="active",
        date_of_joining=date(2026, 1, 1),
        password_hash="mock_hash"
    )
    emp2 = StaffEmployee(
        id=2,
        emp_code="MR10025",
        full_name="Subhash Kumar Kari",
        department_id=1,
        role_id=1,
        is_quarterly_bonus_eligible=True,
        status="active",
        date_of_joining=date(2026, 1, 1),
        password_hash="mock_hash"
    )
    emp3 = StaffEmployee(
        id=3,
        emp_code="MR10099",
        full_name="Non Eligible Employee",
        department_id=1,
        role_id=1,
        is_quarterly_bonus_eligible=False,
        status="active",
        date_of_joining=date(2026, 1, 1),
        password_hash="mock_hash"
    )
    db.add_all([emp1, emp2, emp3])
    db.commit()

    # Seed Quarterly Bonus Configurations
    config1 = StaffQuarterlyBonusConfig(
        id=1,
        period_name="Aug-Sep 2026",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 9, 30),
        min_target_files=50,
        base_bonus_per_file=150.0,
        kra_activity_threshold_pct=80.0,
        high_performance_multiplier=1.2,
        low_performance_multiplier=0.5,
        is_active=True
    )
    db.add(config1)
    db.commit()
    
    db.close()
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test_temp.db"):
        try:
            os.remove("test_temp.db")
        except Exception:
            pass


def test_bonus_models_and_columns():
    db = TestingSessionLocal()
    # Check if configurations are present
    configs = db.query(StaffQuarterlyBonusConfig).all()
    assert len(configs) == 1
    assert configs[0].period_name == "Aug-Sep 2026"
    assert configs[0].min_target_files == 50
    assert float(configs[0].base_bonus_per_file) == 150.0

    # Check if employee has the quarterly eligibility field
    emp = db.query(StaffEmployee).filter_by(emp_code="MR10016").first()
    assert emp is not None
    assert emp.is_quarterly_bonus_eligible is True

    emp_non = db.query(StaffEmployee).filter_by(emp_code="MR10099").first()
    assert emp_non is not None
    assert emp_non.is_quarterly_bonus_eligible is False
    db.close()


def test_bonus_calculation_logic():
    db = TestingSessionLocal()
    emp1 = db.query(StaffEmployee).filter_by(emp_code="MR10016").first()

    # 1. Seed CRM Leads (Completed Solar Files)
    # Target is 50 files. Let's seed 55 completed solar files.
    for i in range(55):
        lead = CRMLead(
            id=100 + i,
            name=f"Solar Client {i}",
            phone=f"90000000{i:02d}",
            category_id=1,
            company_id=1,
            solar_pipeline_status="completed",
            deal_value=20000.0,
            field_staff_id=emp1.id,
            actual_close_date=datetime(2026, 8, 15, 12, 0, 0)
        )
        db.add(lead)
    
    # 2. Seed KRA Performance
    # Let's seed KRA daily instances (8 out of 10 approved -> 80% KRA score)
    for i in range(10):
        kra_instance = StaffKRADailyInstance(
            id=500 + i,
            employee_id=emp1.id,
            kra_assignment_id=1,
            kra_template_id=1,
            instance_date=date(2026, 8, i + 1),
            completion_status="completed",
            manager_review_status="approved" if i < 8 else "rejected"
        )
        db.add(kra_instance)

    # 3. Seed Activity Score
    # Log 400 total minutes against a period that requires 500 minutes -> 80% Activity score
    time_log = StaffActivityTimeLog(
        id=1000,
        employee_id=emp1.id,
        date=date(2026, 8, 5),
        source_type="kra",
        required_minutes=500,
        completed_minutes=400
    )
    db.add(time_log)
    db.commit()

    # Call endpoint simulating logged in employee (MR10016)
    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    app.dependency_overrides[get_current_staff_user] = lambda: emp1
    
    # Test Case 1: Target Met (55 >= 50) and Combined Performance Met (Avg of 80% KRA + 80% Activity = 80% >= 80% threshold) -> Multiplier 1.2x
    response = client.get("/api/v1/staff/performance/quarterly-bonus")
    if response.status_code != 200:
        print("FAILURE STATUS:", response.status_code)
        print("FAILURE RESP TEXT:", response.text)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["eligible"] is True
    
    stats = res_data["stats"]
    assert stats["completed_files"] == 55
    assert stats["target_met"] is True
    assert stats["kra_score"] == 80.0
    assert stats["activity_score"] == 80.0
    assert stats["combined_score"] == 80.0
    assert stats["multiplier"] == 1.2
    # Payout should be: 55 completed files * ₹150 * 1.2 = ₹9,900
    assert stats["estimated_payout"] == 9900.0

    # Let's adjust KRA Daily Instances to reduce KRA performance
    # Make it 6 approved -> 60% KRA score, which averages to 70% with 80% Activity, below the 80% threshold.
    # Yields multiplier of 0.5x.
    kra_instances = db.query(StaffKRADailyInstance).filter_by(employee_id=emp1.id).all()
    for idx, inst in enumerate(kra_instances):
        if idx == 7:  # Change one approved to rejected
            inst.manager_review_status = "rejected"
    db.commit()

    # Test Case 2: Target Met (55 >= 50) and Combined Performance Unmet (Avg of 70% < 80% threshold) -> Multiplier 0.5x
    response = client.get("/api/v1/staff/performance/quarterly-bonus")
    assert response.status_code == 200
    res_data = response.json()
    
    stats = res_data["stats"]
    assert stats["completed_files"] == 55
    assert stats["target_met"] is True
    assert stats["kra_score"] == 70.0
    assert stats["combined_score"] == 75.0
    assert stats["multiplier"] == 0.5
    # Payout should be: 55 completed files * ₹150 * 0.5 = ₹4,125
    assert stats["estimated_payout"] == 4125.0

    # Test Case 3: Target Not Met (e.g. less than 50 completed files) -> Payout = 0
    # Let's delete some CRM leads so we only have 40 completed solar files
    leads = db.query(CRMLead).all()
    for lead in leads[40:]:
        db.delete(lead)
    db.commit()

    response = client.get("/api/v1/staff/performance/quarterly-bonus")
    assert response.status_code == 200
    res_data = response.json()
    
    stats = res_data["stats"]
    assert stats["completed_files"] == 40
    assert stats["target_met"] is False
    assert stats["estimated_payout"] == 0.0

    app.dependency_overrides.pop(get_current_staff_user, None)
    db.close()


def test_non_eligible_employee():
    db = TestingSessionLocal()
    emp_non = db.query(StaffEmployee).filter_by(emp_code="MR10099").first()

    from app.api.v1.endpoints.staff_auth import get_current_staff_user
    app.dependency_overrides[get_current_staff_user] = lambda: emp_non
    
    response = client.get("/api/v1/staff/performance/quarterly-bonus")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["eligible"] is False
    assert res_data["stats"]["estimated_payout"] == 0.0
    
    app.dependency_overrides.pop(get_current_staff_user, None)
    db.close()


if __name__ == "__main__":
    import sys
    print("Running quarterly bonus tests...")
    try:
        # Call setup manually
        generator = setup_db()
        next(generator)
        
        print("Running: test_bonus_models_and_columns...")
        test_bonus_models_and_columns()
        print("Passed: test_bonus_models_and_columns")
        
        print("Running: test_bonus_calculation_logic...")
        test_bonus_calculation_logic()
        print("Passed: test_bonus_calculation_logic")
        
        print("Running: test_non_eligible_employee...")
        test_non_eligible_employee()
        print("Passed: test_non_eligible_employee")
        
        # Call cleanup manually
        try:
            next(generator)
        except StopIteration:
            pass
            
        print("\nALL TESTS PASSED SUCCESSFULLY! (100% SUCCESS RATE)")
        sys.exit(0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
