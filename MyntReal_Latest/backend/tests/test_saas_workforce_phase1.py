"""
MYNTOS SAAS WORKFORCE MANAGEMENT — PHASE 1 VALIDATION TEST SUITE
23 Comprehensive Authenticated HTTP Tests for Phase 1 Foundation:
- Employee Management (1-5)
- Department Management (6-9)
- Task Management (10-14)
- KRA Performance (15-19)
- Workforce Cockpit & Overview (20-23)
"""

import sys
import os
import requests
from datetime import timedelta, date

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffDepartment
from app.models.staff_accounts import AssociatedCompany
from app.models.staff_tasks import StaffTask
from app.models.staff_kra import StaffKRATemplate
from app.models.platform_b2b import PlatformSubscription, PlatformClient

BASE_URL = "http://localhost:8000/api/v1"

def generate_token(emp_id: int) -> str:
    db = SessionLocal()
    try:
        emp = db.query(StaffEmployee).filter(StaffEmployee.id == emp_id).first()
        if not emp:
            raise ValueError(f"Employee {emp_id} not found")
        return SecurityManager.create_access_token(
            data={
                "sub": str(emp.id),
                "emp_code": emp.emp_code,
                "email": emp.email,
                "role": emp.role.role_code if emp.role else "tenant_admin",
                "staff_type": getattr(emp, "staff_type", "MN_STAFF"),
                "admin_scope": getattr(emp, "admin_scope", "CLIENT_SPECIFIC"),
                "base_company_id": emp.base_company_id,
                "tenant_id": getattr(emp, "tenant_id", 1) or 1,
                "token_version": getattr(emp, "token_version", 1) or 1,
                "team_tag": emp.team_tag,
                "user_type": "staff"
            },
            expires_delta=timedelta(hours=24)
        )
    finally:
        db.close()


def run_tests():
    print("=" * 80)
    print("STARTING MYNTOS SAAS WORKFORCE MANAGEMENT PHASE 1 TEST SUITE (23 TESTS)")
    print("=" * 80)

    # Setup actors
    # Company A: Test Solar (127), Admin: Emp 11043 (TESO_ADMIN)
    # Company B: Apex Infotech (94), Admin: Emp 303 (AIS_ADMIN)
    token_a = generate_token(11043)
    token_b = generate_token(303)

    headers_a = {"Authorization": f"Bearer {token_a}", "Content-Type": "application/json"}
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}

    results = []
    created_dept_id = None
    created_emp_id = None
    created_task_id = None
    created_kra_id = None

    def record(num, name, passed, detail=""):
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] Test {num:02d}: {name} - {detail}")
        results.append((num, name, passed, detail))

    # =========================================================================
    # 1. EMPLOYEE TESTS (1-5)
    # =========================================================================
    print("\n--- GROUP 1: EMPLOYEE MANAGEMENT TESTS (1-5) ---")

    # Test 1: Create user/employee in Company A -> Success, company_id stamped
    test_user_payload = {
        "full_name": "Test Solar Worker",
        "email": "worker1_phase1@testsolar.com",
        "phone": "+919876500001",
        "role_id": 5,
        "department_id": None,
        "reporting_manager_id": 11043,
        "date_of_joining": str(date.today()),
        "assigned_modules": ["STAFF_HRMS"]
    }
    r = requests.post(f"{BASE_URL}/platform-b2b/tenant/users", json=test_user_payload, headers=headers_a)
    if r.status_code in [200, 201]:
        created_user_data = r.json().get("user", {})
        created_emp_id = created_user_data.get("id")
        cid = created_user_data.get("base_company_id")
        record(1, "Create employee in Company A", cid == 127, f"HTTP {r.status_code}, Emp ID: {created_emp_id}, Company: {cid}")
    elif r.status_code == 400 and ("already in use" in r.text or "already exists" in r.text):
        db = SessionLocal()
        existing = db.query(StaffEmployee).filter(StaffEmployee.email == "worker1_phase1@testsolar.com").first()
        created_emp_id = existing.id if existing else None
        db.close()
        record(1, "Create employee in Company A (idempotent)", True, f"Existing worker ID: {created_emp_id}")
    else:
        record(1, "Create employee in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 2: Tenant seat limit enforcement -> Adding beyond plan limit blocked
    db = SessionLocal()
    sub = db.query(PlatformSubscription).filter(PlatformSubscription.client_id == 190).first()
    orig_seat_count = sub.seat_count if sub else None
    if sub:
        current_users_cnt = db.query(StaffEmployee).filter(StaffEmployee.base_company_id == 127, StaffEmployee.status == "active").count()
        sub.seat_count = current_users_cnt
        db.commit()
    db.close()

    overflow_payload = {
        "full_name": "Test Solar Overflow Worker",
        "email": "overflow_phase1@testsolar.com",
        "phone": "+919876500002",
        "role_id": 5
    }
    r = requests.post(f"{BASE_URL}/platform-b2b/tenant/users", json=overflow_payload, headers=headers_a)
    record(2, "Seat limit enforcement (blocked at quota)", r.status_code in [400, 403] and ("Seat" in r.text or "seat" in r.text), f"HTTP {r.status_code}: {r.text[:80]}")

    # Restore seat count
    db = SessionLocal()
    sub = db.query(PlatformSubscription).filter(PlatformSubscription.client_id == 190).first()
    if sub and orig_seat_count is not None:
        sub.seat_count = orig_seat_count
        db.commit()
    db.close()

    # Test 3: Cross-company department assignment -> Cannot assign Company B department to Company A employee
    db = SessionLocal()
    dept_b = db.query(StaffDepartment).filter(StaffDepartment.company_id == 94, StaffDepartment.name == "Apex Phase1 Custom Dept").first()
    if not dept_b:
        dept_b = StaffDepartment(name="Apex Phase1 Custom Dept", company_id=94, is_active=True)
        db.add(dept_b)
        db.commit()
    dept_b_id = dept_b.id
    db.close()

    cross_dept_payload = {
        "full_name": "Test Cross Dept Worker",
        "email": "cross_dept@testsolar.com",
        "phone": "+919876500003",
        "role_id": 5,
        "department_id": dept_b_id
    }
    r = requests.post(f"{BASE_URL}/platform-b2b/tenant/users", json=cross_dept_payload, headers=headers_a)
    record(3, "Cross-company department assignment blocked", r.status_code in [400, 403], f"HTTP {r.status_code}: {r.text[:80]}")

    # Test 4: Cross-company manager assignment -> Cannot assign Company B manager to Company A employee
    cross_mgr_payload = {
        "full_name": "Test Cross Mgr Worker",
        "email": "cross_mgr@testsolar.com",
        "phone": "+919876500004",
        "role_id": 5,
        "reporting_manager_id": 303  # AIS_ADMIN belongs to Company 94
    }
    r = requests.post(f"{BASE_URL}/platform-b2b/tenant/users", json=cross_mgr_payload, headers=headers_a)
    record(4, "Cross-company manager assignment blocked", r.status_code in [400, 403], f"HTTP {r.status_code}: {r.text[:80]}")

    # Test 5: Update employee within company boundary -> Success
    if created_emp_id:
        update_payload = {
            "designation": "Solar Senior Field Tech",
            "phone": "+919876509999"
        }
        r = requests.put(f"{BASE_URL}/platform-b2b/tenant/users/{created_emp_id}", json=update_payload, headers=headers_a)
        record(5, "Update employee within company boundary", r.status_code == 200, f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(5, "Update employee within company boundary", False, "Skipped: created_emp_id missing")

    # =========================================================================
    # 2. DEPARTMENT TESTS (6-9)
    # =========================================================================
    print("\n--- GROUP 2: DEPARTMENT MANAGEMENT TESTS (6-9) ---")

    # Test 6: List departments for Company A -> Returns Company A + global, zero Company B custom
    r = requests.get(f"{BASE_URL}/staff/departments", headers=headers_a)
    if r.status_code == 200:
        depts = r.json().get("departments", [])
        has_dept_b = any(d.get("id") == dept_b_id for d in depts)
        record(6, "List departments (Company A + global, zero Company B)", not has_dept_b and len(depts) > 0,
               f"Total depts: {len(depts)}, Contains Dept B: {has_dept_b}")
    else:
        record(6, "List departments", False, f"HTTP {r.status_code}: {r.text}")

    # Test 7: Create custom department in Company A -> Success, company_id stamped
    custom_dept_payload = {
        "name": "Test Solar Quality & Safety",
        "description": "Custom QA department for solar installations",
        "department_code": "TS_QA_01"
    }
    r = requests.post(f"{BASE_URL}/staff/departments", json=custom_dept_payload, headers=headers_a)
    if r.status_code in [200, 201]:
        created_dept = r.json().get("department", {})
        created_dept_id = created_dept.get("id")
        cid = created_dept.get("company_id")
        record(7, "Create custom department in Company A", cid == 127, f"HTTP {r.status_code}, Dept ID: {created_dept_id}, Company: {cid}")
    elif r.status_code == 400 and "already exists" in r.text:
        db = SessionLocal()
        d_exist = db.query(StaffDepartment).filter(StaffDepartment.company_id == 127, StaffDepartment.name == "Test Solar Quality & Safety").first()
        created_dept_id = d_exist.id if d_exist else None
        db.close()
        record(7, "Create custom department (idempotent)", True, f"Existing Dept ID: {created_dept_id}")
    else:
        record(7, "Create custom department in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 8: Edit Company A custom department -> Success
    if created_dept_id:
        edit_dept_payload = {
            "name": "Test Solar Quality & Safety Updated",
            "description": "Updated QA and Compliance"
        }
        r = requests.put(f"{BASE_URL}/staff/departments/{created_dept_id}", json=edit_dept_payload, headers=headers_a)
        record(8, "Edit Company A custom department", r.status_code == 200, f"HTTP {r.status_code}")
    else:
        record(8, "Edit Company A custom department", False, "Skipped: created_dept_id missing")

    # Test 9: Cross-company department isolation -> Company B cannot edit Company A's department
    if created_dept_id:
        tamper_payload = {"name": "Hacked Dept Name"}
        r = requests.put(f"{BASE_URL}/staff/departments/{created_dept_id}", json=tamper_payload, headers=headers_b)
        record(9, "Cross-company department isolation (Company B blocked)", r.status_code in [403, 404], f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(9, "Cross-company department isolation", False, "Skipped: created_dept_id missing")

    # =========================================================================
    # 3. TASK TESTS (10-14)
    # =========================================================================
    print("\n--- GROUP 3: TASK MANAGEMENT TESTS (10-14) ---")

    # Test 10: Create task in Company A -> Success, company_id stamped
    task_payload = {
        "title": "Solar Inverter Calibration",
        "description": "Check Phase 1 inverter telemetry",
        "task_type": "standard",
        "priority": "high",
        "due_date": str(date.today()),
        "primary_assignee_id": 11043
    }
    r = requests.post(f"{BASE_URL}/staff/tasks/", json=task_payload, headers=headers_a)
    if r.status_code in [200, 201]:
        task_data = r.json()
        created_task_id = task_data.get("id") or task_data.get("task", {}).get("id")
        db = SessionLocal()
        t_row = db.query(StaffTask).filter(StaffTask.id == created_task_id).first()
        t_cid = t_row.company_id if t_row else None
        db.close()
        record(10, "Create task in Company A", t_cid == 127, f"HTTP {r.status_code}, Task ID: {created_task_id}, Company: {t_cid}")
    else:
        record(10, "Create task in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 11: Cross-company task assignee -> Cannot assign Company B employee (303) to Company A task
    cross_task_payload = {
        "title": "Invalid Cross Task",
        "description": "Should fail due to cross company assignee",
        "due_date": str(date.today()),
        "primary_assignee_id": 303  # Company 94
    }
    r = requests.post(f"{BASE_URL}/staff/tasks/", json=cross_task_payload, headers=headers_a)
    record(11, "Cross-company task assignee blocked", r.status_code in [400, 403], f"HTTP {r.status_code}: {r.text[:80]}")

    # Test 12: List tasks in Company A -> Returns only Company A tasks (zero leakage)
    r = requests.get(f"{BASE_URL}/staff/tasks/", headers=headers_a)
    if r.status_code == 200:
        tasks_list = r.json().get("tasks", [])
        all_company_a = all(t.get("company_id") in [127, None] for t in tasks_list)
        record(12, "List tasks (strictly scoped to Company A)", all_company_a and len(tasks_list) > 0,
               f"Count: {len(tasks_list)}, All Company 127: {all_company_a}")
    else:
        record(12, "List tasks in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 13: Access/manipulate Company A task from Company B -> Blocked (403/404)
    if created_task_id:
        tamper_task_payload = {"title": "Company B Tampered Title"}
        r = requests.put(f"{BASE_URL}/staff/tasks/{created_task_id}", json=tamper_task_payload, headers=headers_b)
        record(13, "Cross-company task manipulation blocked", r.status_code in [403, 404], f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(13, "Cross-company task manipulation blocked", False, "Skipped: created_task_id missing")

    # Test 14: Assignable employees endpoint -> Scoped strictly to Company A
    r = requests.get(f"{BASE_URL}/staff/tasks/assignable-employees", headers=headers_a)
    if r.status_code == 200:
        assignables = r.json().get("employees", [])
        has_ais = any(e.get("id") == 303 for e in assignables)
        record(14, "Assignable employees scoped to Company A", not has_ais and len(assignables) > 0,
               f"Count: {len(assignables)}, Contains Company B: {has_ais}")
    else:
        record(14, "Assignable employees endpoint", False, f"HTTP {r.status_code}: {r.text}")

    # =========================================================================
    # 4. KRA TESTS (15-19)
    # =========================================================================
    print("\n--- GROUP 4: KRA PERFORMANCE TESTS (15-19) ---")

    # Test 15: Create KRA template in Company A -> Success, company_id stamped
    kra_payload = {
        "title": "Daily Solar Panel Inspection",
        "description": "Inspect 20 rooftop solar strings and record voltage",
        "frequency": "daily",
        "frequency_config": {"pattern": "daily"},
        "is_mandatory": True,
        "estimated_time_minutes": 60
    }
    r = requests.post(f"{BASE_URL}/staff/kra/templates", json=kra_payload, headers=headers_a)
    if r.status_code in [200, 201]:
        created_kra = r.json()
        created_kra_id = created_kra.get("id") or created_kra.get("template_id")
        db = SessionLocal()
        k_row = db.query(StaffKRATemplate).filter(StaffKRATemplate.id == created_kra_id).first()
        k_cid = k_row.company_id if k_row else None
        db.close()
        record(15, "Create KRA template in Company A", k_cid == 127, f"HTTP {r.status_code}, KRA ID: {created_kra_id}, Company: {k_cid}")
    else:
        record(15, "Create KRA template in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 16: List KRA templates in Company A -> Returns only Company A templates (zero VGK/Company B leakage)
    r = requests.get(f"{BASE_URL}/staff/kra/templates", headers=headers_a)
    if r.status_code == 200:
        kras_list = r.json().get("templates", [])
        db = SessionLocal()
        vgk_template_ids = [t.id for t in db.query(StaffKRATemplate).filter(StaffKRATemplate.company_id == 2).all()]
        db.close()
        leaked_vgk = any(k.get("id") in vgk_template_ids for k in kras_list)
        record(16, "List KRA templates (zero VGK/Company B leakage)", not leaked_vgk and len(kras_list) > 0,
               f"Total templates: {len(kras_list)}, Leaked VGK: {leaked_vgk}")
    else:
        record(16, "List KRA templates in Company A", False, f"HTTP {r.status_code}: {r.text}")

    # Test 17: Approve KRA template as SaaS Tenant Admin -> Success without VGK4U role error
    if created_kra_id:
        db = SessionLocal()
        k_row = db.query(StaffKRATemplate).filter(StaffKRATemplate.id == created_kra_id).first()
        k_row.approval_status = "pending_approval"
        db.commit()
        db.close()

        approve_payload = {"notes": "Approved by Test Solar Admin"}
        r = requests.post(f"{BASE_URL}/staff/kra/templates/{created_kra_id}/approve", json=approve_payload, headers=headers_a)
        record(17, "Approve KRA template as Tenant Admin", r.status_code == 200, f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(17, "Approve KRA template as Tenant Admin", False, "Skipped: created_kra_id missing")

    # Test 18: Cross-company KRA assignment -> Cannot assign Company B employee to Company A KRA
    if created_kra_id:
        cross_assign_payload = {
            "employee_ids": ["AIS_ADMIN"],  # Emp 303 in Company 94
            "effective_from": str(date.today())
        }
        r = requests.post(f"{BASE_URL}/staff/kra/templates/{created_kra_id}/assign", json=cross_assign_payload, headers=headers_a)
        record(18, "Cross-company KRA assignment blocked", r.status_code in [400, 403], f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(18, "Cross-company KRA assignment", False, "Skipped: created_kra_id missing")

    # Test 19: Cross-company KRA template manipulation -> Company B blocked from deactivating/deleting Company A template
    if created_kra_id:
        r = requests.delete(f"{BASE_URL}/staff/kra/templates/{created_kra_id}", headers=headers_b)
        record(19, "Cross-company KRA manipulation blocked (Company B)", r.status_code in [403, 404], f"HTTP {r.status_code}: {r.text[:80]}")
    else:
        record(19, "Cross-company KRA manipulation", False, "Skipped: created_kra_id missing")

    # =========================================================================
    # 5. WORKFORCE DASHBOARD & COCKPIT TESTS (20-23)
    # =========================================================================
    print("\n--- GROUP 5: WORKFORCE COCKPIT & OVERVIEW TESTS (20-23) ---")

    # Test 20: Call /api/v1/staff/overview as Tenant Admin -> Success 200
    r = requests.get(f"{BASE_URL}/staff/overview", headers=headers_a)
    if r.status_code == 200:
        emp_records = r.json()
        record(20, "Workforce Overview (/staff/overview) access as Tenant Admin", True, f"HTTP 200, Returned {len(emp_records)} staff rows")
    else:
        record(20, "Workforce Overview access as Tenant Admin", False, f"HTTP {r.status_code}: {r.text[:100]}")

    # Test 21: Verify snapshot cross-company isolation -> Response strictly contains only Company A employees
    if r.status_code == 200:
        emp_records = r.json()
        company_ids_found = set(e.get("company_id") for e in emp_records if e.get("company_id"))
        only_company_a = company_ids_found.issubset({127})
        record(21, "Workforce Overview cross-company isolation (zero leakage)", only_company_a and len(emp_records) > 0,
               f"Companies found: {company_ids_found}, Strict Company 127: {only_company_a}")
    else:
        record(21, "Workforce Overview cross-company isolation", False, "Skipped due to Test 20 failure")

    # Test 22: Call /api/v1/staff/workforce-summary -> Success 200 with company-scoped KPI cards
    r = requests.get(f"{BASE_URL}/staff/workforce-summary", headers=headers_a)
    if r.status_code == 200:
        summary_data = r.json()
        cid = summary_data.get("company_id")
        has_keys = "total_employees" in summary_data and "total_departments" in summary_data and "tasks" in summary_data and "kra" in summary_data
        record(22, "Workforce Summary KPI cockpit (/staff/workforce-summary)", cid == 127 and has_keys,
               f"Company: {cid}, Employees: {summary_data.get('total_employees')}, Depts: {summary_data.get('total_departments')}")
    else:
        record(22, "Workforce Summary KPI cockpit", False, f"HTTP {r.status_code}: {r.text[:100]}")

    # Test 23: Non-authorized / cross-tenant access to overview -> Gated with 403 Forbidden
    token_teco = generate_token(302)
    headers_teco = {"Authorization": f"Bearer {token_teco}", "Content-Type": "application/json"}
    r = requests.get(f"{BASE_URL}/staff/overview", headers=headers_teco)
    record(23, "Unauthorized tenant access to overview gated (403)", r.status_code == 403,
           f"HTTP {r.status_code}: {r.text[:80]}")

    # =========================================================================
    # TEARDOWN & CLEANUP
    # =========================================================================
    print("\n--- TEARDOWN & CLEANUP ---")
    db = SessionLocal()
    try:
        if created_kra_id:
            db.query(StaffKRATemplate).filter(StaffKRATemplate.id == created_kra_id).delete()
        if created_task_id:
            db.query(StaffTask).filter(StaffTask.id == created_task_id).delete()
        if created_dept_id:
            db.query(StaffDepartment).filter(StaffDepartment.id == created_dept_id).delete()
        if dept_b_id:
            db.query(StaffDepartment).filter(StaffDepartment.id == dept_b_id).delete()
        if created_emp_id:
            db.query(StaffEmployee).filter(StaffEmployee.id == created_emp_id).delete()
        db.commit()
        print("Teardown completed cleanly.")
    except Exception as e:
        db.rollback()
        print(f"Teardown notice: {e}")
    finally:
        db.close()

    # =========================================================================
    # SUMMARY REPORT
    # =========================================================================
    print("\n" + "=" * 80)
    print("PHASE 1 IMPLEMENTATION TEST RESULTS SUMMARY")
    print("=" * 80)
    passed_cnt = sum(1 for _, _, p, _ in results if p)
    failed_cnt = sum(1 for _, _, p, _ in results if not p)
    print(f"TOTAL TESTS: {len(results)} | PASSED: {passed_cnt} | FAILED: {failed_cnt}")
    for num, name, passed, detail in results:
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] #{num:02d} {name}: {detail}")
    print("=" * 80)
    return failed_cnt == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
