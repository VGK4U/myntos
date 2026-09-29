"""
Developer Staff Account Seeding Script
Populates required reference tables (associated_companies, staff_roles, staff_departments)
and developer test accounts (MR10022 - Ms. Anusha Moyyi, MN10016, MR10001, VIEWTEST) in local development database.
"""

import sys
import os
from datetime import date
from sqlalchemy import func
from werkzeug.security import generate_password_hash

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.staff import StaffRole, StaffDepartment, StaffEmployee
from app.models.staff_accounts import AssociatedCompany


def seed_database():
    print("[DEV-SEED] Starting developer database seeding...")
    
    from app.models.staff import StaffEmployeeDepartment, StaffSetting, StaffAuditLog, StaffNdaAcceptance, StaffNdaVersion
    from app.models.community_service import CommunityService, CommunityRegistration
    from app.models.staff_accounts import OfficialPartner, VGKTeamCommissionConfig
    from app.models.crm import CRMLead
    from app.services.sandbox_seeder import seed_sandbox_data

    AssociatedCompany.__table__.create(bind=engine, checkfirst=True)
    StaffRole.__table__.create(bind=engine, checkfirst=True)
    StaffDepartment.__table__.create(bind=engine, checkfirst=True)
    StaffEmployee.__table__.create(bind=engine, checkfirst=True)
    StaffEmployeeDepartment.__table__.create(bind=engine, checkfirst=True)
    StaffSetting.__table__.create(bind=engine, checkfirst=True)
    StaffAuditLog.__table__.create(bind=engine, checkfirst=True)
    StaffNdaVersion.__table__.create(bind=engine, checkfirst=True)
    StaffNdaAcceptance.__table__.create(bind=engine, checkfirst=True)
    OfficialPartner.__table__.create(bind=engine, checkfirst=True)
    VGKTeamCommissionConfig.__table__.create(bind=engine, checkfirst=True)
    CommunityService.__table__.create(bind=engine, checkfirst=True)
    CommunityRegistration.__table__.create(bind=engine, checkfirst=True)
    CRMLead.__table__.create(bind=engine, checkfirst=True)
    
    session = SessionLocal()
    try:
        # 1. Seed Associated Companies (IDs 1 to 5 to match data_companies [2, 3, 4, 5])
        for c_id in range(1, 6):
            company = session.query(AssociatedCompany).filter_by(id=c_id).first()
            if not company:
                company = AssociatedCompany(
                    id=c_id,
                    company_name=f"Development Company {c_id}",
                    company_code=f"COMPANY_{c_id}",
                    is_active=True
                )
                session.add(company)
                session.commit()
                print(f"  [+] Created AssociatedCompany id={c_id}")

        # 2. Seed Staff Roles
        roles_data = [
            {"id": 1, "role_code": "admin", "role_name": "System Administrator", "hierarchy_level": 1},
            {"id": 2, "role_code": "manager", "role_name": "Manager", "hierarchy_level": 2},
            {"id": 3, "role_code": "staff", "role_name": "Staff Employee", "hierarchy_level": 3},
            {"id": 10, "role_code": "telecaller", "role_name": "Sales Telecaller", "hierarchy_level": 3},
            {"id": 17, "role_code": "tenant_admin", "role_name": "Tenant Administrator", "hierarchy_level": 1},
        ]
        for r_info in roles_data:
            r = session.query(StaffRole).filter((StaffRole.id == r_info["id"]) | (StaffRole.role_code == r_info["role_code"])).first()
            if not r:
                r = StaffRole(
                    id=r_info["id"],
                    role_code=r_info["role_code"],
                    role_name=r_info["role_name"],
                    hierarchy_level=r_info["hierarchy_level"],
                    is_active=True
                )
                session.add(r)
                session.commit()
                print(f"  [+] Created StaffRole {r_info['role_code']} (id={r_info['id']})")

        # 3. Seed Staff Departments
        dept_data = [
            {"id": 1, "department_code": "SALES", "name": "Sales Department"},
            {"id": 13, "department_code": "TELECALLING", "name": "Telecalling Department"}
        ]
        for d_info in dept_data:
            dept = session.query(StaffDepartment).filter_by(id=d_info["id"]).first()
            if not dept:
                dept = StaffDepartment(
                    id=d_info["id"],
                    name=d_info["name"],
                    department_code=d_info["department_code"],
                    is_active=True
                )
                session.add(dept)
                session.commit()
                print(f"  [+] Created StaffDepartment id={d_info['id']} ({d_info['name']})")

        # 4. Seed Dev Staff Accounts
        default_hash = generate_password_hash("Admin@123", method="pbkdf2:sha256")
        
        dev_accounts = [
            {
                "emp_code": "MR10022",
                "first_name": "Anusha",
                "last_name": "Moyyi",
                "full_name": "Ms. Anusha Moyyi",
                "email": "anusha@myntreal.com",
                "phone": "9876543210",
                "role_id": 10,
                "department_id": 13,
                "base_company_id": 2,
                "data_companies": [1, 2, 3, 4, 5],
                "staff_type": "MYNT_REAL",
            },
            {
                "emp_code": "MN10016",
                "first_name": "Test",
                "last_name": "MN Staff",
                "full_name": "Test MN Staff",
                "email": "mn10016@myntreal.com",
                "phone": "9876543211",
                "role_id": 3,
                "department_id": 1,
                "base_company_id": 1,
                "data_companies": [1],
                "staff_type": "MN_STAFF",
            },
            {
                "emp_code": "MR10001",
                "first_name": "Admin",
                "last_name": "User",
                "full_name": "Admin User",
                "email": "admin@myntreal.com",
                "phone": "9876543212",
                "role_id": 1,
                "department_id": 1,
                "base_company_id": 1,
                "data_companies": [1],
                "staff_type": "MYNT_REAL",
            },
            {
                "emp_code": "VIEWTEST",
                "first_name": "View",
                "last_name": "TEST",
                "full_name": "View TEST",
                "email": "viewtest@myntreal.com",
                "phone": "9876543213",
                "role_id": 3,
                "department_id": 1,
                "base_company_id": 1,
                "data_companies": [1],
                "staff_type": "MN_STAFF",
            },
        ]

        for acc in dev_accounts:
            code_upper = acc["emp_code"].upper()
            emp = session.query(StaffEmployee).filter(
                (func.lower(StaffEmployee.emp_code) == code_upper.lower()) | 
                (func.lower(StaffEmployee.email) == acc["email"].lower())
            ).first()
            
            if not emp:
                emp = StaffEmployee(
                    emp_code=code_upper,
                    first_name=acc["first_name"],
                    last_name=acc["last_name"],
                    full_name=acc["full_name"],
                    email=acc["email"],
                    phone=acc["phone"],
                    role_id=acc["role_id"],
                    department_id=acc["department_id"],
                    base_company_id=acc.get("base_company_id", 1),
                    data_companies=acc.get("data_companies", [1]),
                    status="active",
                    staff_type=acc["staff_type"],
                    password_hash=default_hash,
                    requires_password_change=False,
                    date_of_joining=date(2025, 1, 1),
                )
                session.add(emp)
                session.commit()
                print(f"  [+] Seeded staff account {code_upper} ({acc['full_name']})")
            else:
                emp.emp_code = code_upper
                emp.first_name = acc["first_name"]
                emp.last_name = acc["last_name"]
                emp.full_name = acc["full_name"]
                emp.email = acc["email"]
                emp.role_id = acc["role_id"]
                emp.department_id = acc["department_id"]
                emp.base_company_id = acc.get("base_company_id", 1)
                emp.data_companies = acc.get("data_companies", [1])
                emp.password_hash = default_hash
                emp.status = "active"
                emp.requires_password_change = False
                session.commit()
                print(f"  [=] Updated existing staff account {code_upper} -> {acc['full_name']}")

        try:
            seed_sandbox_data(session)
            session.commit()
            print("  [+] Seeded sandbox community services data")
        except Exception as s_err:
            session.rollback()
            print("  [!] Sandbox data seeding warning:", s_err)

        print("[DEV-SEED] Developer database seeding completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"[DEV-SEED] ERROR during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
