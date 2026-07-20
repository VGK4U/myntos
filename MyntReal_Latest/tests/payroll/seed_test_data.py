"""
DC Protocol Compliant Test Data Seeder for Staff Payroll System
Creates company-segregated test data for E2E testing
"""
import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
sys.path.insert(0, backend_path)
os.chdir(backend_path)

from datetime import datetime, date
from decimal import Decimal
import json

from app.core.database import SessionLocal
from app.models.staff_payroll import (
    StaffPayrollProfile, StaffPayrollStatutoryConfig, StaffPayrollCycle,
    StaffPayrollRun, StaffPayrollDeduction, StaffPayrollDocument,
    StaffConsultantInvoice, StaffPayrollAuditLog, StaffPayrollAllowanceCatalog
)
from sqlalchemy import text

def get_indian_datetime():
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)

def seed_test_data():
    db = SessionLocal()
    try:
        print("[DC-SEED] Starting DC Protocol compliant test data seeding...")
        
        test_companies = db.execute(text("SELECT id, company_name FROM associated_companies WHERE id IN (1,2,3,4) AND is_active = true LIMIT 4")).fetchall()
        if not test_companies:
            print("[DC-SEED] ERROR: No companies found in associated_companies table.")
            return
        
        print(f"[DC-SEED] Found {len(test_companies)} companies for DC-segregated seeding")
        
        test_employees = db.execute(text("""
            SELECT id, full_name, designation, department_id, base_company_id 
            FROM staff_employees 
            WHERE status = 'active' AND (is_deleted IS NULL OR is_deleted = false)
            LIMIT 10
        """)).fetchall()
        
        if not test_employees:
            print("[DC-SEED] WARNING: No active employees found. Test data will be limited.")
            test_employees = []
        
        print(f"[DC-SEED] Found {len(test_employees)} employees for testing")
        
        for company_id, company_name in test_companies:
            print(f"\n[DC-SEED] === Seeding Company {company_id}: {company_name} ===")
            
            existing_catalog = db.query(StaffPayrollAllowanceCatalog).filter(
                StaffPayrollAllowanceCatalog.company_id == company_id,
                StaffPayrollAllowanceCatalog.is_active == True
            ).first()
            
            if not existing_catalog:
                allowances = [
                    {"name": "Conveyance Allowance", "code": f"CONV_{company_id}", "value": 1600, "max": 5000},
                    {"name": "Medical Allowance", "code": f"MED_{company_id}", "value": 1250, "max": 2500},
                    {"name": "LTA", "code": f"LTA_{company_id}", "value": 5000, "max": 10000},
                ]
                for idx, allow in enumerate(allowances):
                    catalog = StaffPayrollAllowanceCatalog(
                        company_id=company_id,
                        allowance_name=allow["name"],
                        allowance_code=allow["code"],
                        allowance_description=f"Standard {allow['name']}",
                        is_percentage=False,
                        default_value=Decimal(str(allow["value"])),
                        max_limit=Decimal(str(allow["max"])),
                        is_taxable=True,
                        display_order=idx + 1,
                        is_active=True,
                        created_by_id=1
                    )
                    db.add(catalog)
                print(f"  [DC-SEED] Created {len(allowances)} allowance catalog entries")
            else:
                print(f"  [DC-SEED] Allowance catalog already exists")
            
            company_employees = [e for e in test_employees if e[4] == company_id]
            if not company_employees:
                print(f"  [DC-SEED] No employees in company {company_id}, using first available")
                company_employees = test_employees[:2] if test_employees else []
            
            for emp in company_employees[:3]:
                emp_id, emp_name, designation, department_id, _ = emp
                
                existing_profile = db.query(StaffPayrollProfile).filter(
                    StaffPayrollProfile.employee_id == emp_id,
                    StaffPayrollProfile.company_id == company_id,
                    StaffPayrollProfile.is_active == True
                ).first()
                
                if not existing_profile:
                    ctc_annual = Decimal("600000") + (emp_id * 10000)
                    ctc_monthly = ctc_annual / 12
                    
                    profile = StaffPayrollProfile(
                        employee_id=emp_id,
                        company_id=company_id,
                        employment_type="ONROLE",
                        effective_from=date(2025, 1, 1),
                        ctc_annual=ctc_annual,
                        ctc_monthly=ctc_monthly,
                        basic_pct=Decimal("40"),
                        hra_pct=Decimal("20"),
                        special_allowance=ctc_monthly * Decimal("0.40"),
                        pf_applicable=True,
                        esi_applicable=ctc_annual < Decimal("252000"),
                        pt_applicable=True,
                        tds_applicable=True,
                        is_active=True,
                        created_by_id=1
                    )
                    db.add(profile)
                    print(f"  [DC-SEED] Created salary profile for employee {emp_id}")
                else:
                    print(f"  [DC-SEED] Profile exists for employee {emp_id}")
            
            existing_cycle = db.query(StaffPayrollCycle).filter(
                StaffPayrollCycle.company_id == company_id,
                StaffPayrollCycle.cycle_month == 12,
                StaffPayrollCycle.cycle_year == 2025
            ).first()
            
            if not existing_cycle:
                cycle_code = f"CYC-{company_id}-202512"
                cycle = StaffPayrollCycle(
                    cycle_code=cycle_code,
                    company_id=company_id,
                    cycle_month=12,
                    cycle_year=2025,
                    period_start=date(2025, 12, 1),
                    period_end=date(2025, 12, 31),
                    status="DRAFT",
                    created_by_id=1
                )
                db.add(cycle)
                db.flush()
                
                profiles = db.query(StaffPayrollProfile).filter(
                    StaffPayrollProfile.company_id == company_id,
                    StaffPayrollProfile.is_active == True
                ).limit(3).all()
                
                for profile in profiles:
                    basic = profile.ctc_monthly * profile.basic_pct / 100
                    hra = profile.ctc_monthly * profile.hra_pct / 100
                    gross = profile.ctc_monthly
                    pf = basic * Decimal("0.12")
                    net = gross - pf - Decimal("200")
                    
                    run_code = f"RUN-{company_id}-202512-{profile.employee_id}"
                    run = StaffPayrollRun(
                        run_code=run_code,
                        cycle_id=cycle.id,
                        profile_id=profile.id,
                        employee_id=profile.employee_id,
                        company_id=company_id,
                        eligible_days=31,
                        present_days=28,
                        lop_days=0,
                        ctc_monthly=profile.ctc_monthly,
                        gross_salary=gross,
                        basic_amount=basic,
                        hra_amount=hra,
                        special_allowance=profile.special_allowance,
                        pf_employee=pf,
                        pt_amount=Decimal("200"),
                        total_earnings=gross,
                        total_deductions=pf + Decimal("200"),
                        net_salary=net,
                        status="PENDING",
                        created_by_id=1
                    )
                    db.add(run)
                    db.flush()
                    
                    doc = StaffPayrollDocument(
                        employee_id=profile.employee_id,
                        company_id=company_id,
                        cycle_id=cycle.id,
                        payroll_run_id=run.id,
                        document_type="PAYSLIP",
                        document_code=f"SLIP-{company_id}-202512-{profile.employee_id}",
                        document_title=f"Payslip December 2025",
                        file_path=f"/uploads/payroll/{company_id}/payslip_{profile.employee_id}_202512.pdf",
                        file_name=f"payslip_{profile.employee_id}_202512.pdf",
                        file_size=0,
                        document_date=date(2025, 12, 31),
                        template_data={
                            "employee_name": emp_name or f"Employee {profile.employee_id}",
                            "employee_code": f"EMP{profile.employee_id:04d}",
                            "month": "December",
                            "year": "2025",
                            "days_in_month": 31,
                            "days_worked": 28,
                            "basic_pay": float(basic),
                            "hra": float(hra),
                            "special_allowance": float(profile.special_allowance),
                            "gross_earnings": float(gross),
                            "pf_deduction": float(pf),
                            "esi_deduction": 0,
                            "pt_deduction": 200,
                            "tds_deduction": 0,
                            "total_deductions": float(pf + 200),
                            "net_pay": float(net)
                        },
                        generated_at=get_indian_datetime(),
                        generated_by=1,
                        is_active=True
                    )
                    db.add(doc)
                
                print(f"  [DC-SEED] Created cycle with {len(profiles)} payroll runs")
            else:
                print(f"  [DC-SEED] Cycle for Dec 2025 already exists")
            
            existing_invoice = db.query(StaffConsultantInvoice).filter(
                StaffConsultantInvoice.company_id == company_id
            ).first()
            
            if not existing_invoice:
                first_emp_id = company_employees[0][0] if company_employees else 1
                invoice = StaffConsultantInvoice(
                    company_id=company_id,
                    employee_id=first_emp_id,
                    invoice_number=f"CONS-{company_id}-202512-001",
                    invoice_date=date(2025, 12, 15),
                    service_period_from=date(2025, 12, 1),
                    service_period_to=date(2025, 12, 31),
                    service_description=f"Consulting Services - {company_name}",
                    invoice_amount=Decimal("50000"),
                    gst_applicable=True,
                    gst_rate=Decimal("18"),
                    gst_amount=Decimal("9000"),
                    tds_applicable=True,
                    tds_section="194J",
                    tds_rate=Decimal("10"),
                    tds_amount=Decimal("5000"),
                    total_amount=Decimal("59000"),
                    net_payable=Decimal("54000"),
                    status="DRAFT",
                    created_by_id=1
                )
                db.add(invoice)
                print(f"  [DC-SEED] Created consultant invoice")
            else:
                print(f"  [DC-SEED] Consultant invoice already exists")
        
        db.commit()
        print("\n[DC-SEED] ✅ Test data seeding completed successfully!")
        
        summary = {
            "profiles": db.query(StaffPayrollProfile).filter(StaffPayrollProfile.is_active == True).count(),
            "cycles": db.query(StaffPayrollCycle).count(),
            "runs": db.query(StaffPayrollRun).count(),
            "documents": db.query(StaffPayrollDocument).filter(StaffPayrollDocument.is_active == True).count(),
            "invoices": db.query(StaffConsultantInvoice).count(),
            "allowances": db.query(StaffPayrollAllowanceCatalog).filter(StaffPayrollAllowanceCatalog.is_active == True).count()
        }
        print(f"\n[DC-SEED] Summary: {json.dumps(summary, indent=2)}")
        
        return summary
        
    except Exception as e:
        db.rollback()
        print(f"[DC-SEED] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_data()
