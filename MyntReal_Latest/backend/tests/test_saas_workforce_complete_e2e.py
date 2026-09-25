"""
End-to-End Test Suite for MYNTOS SaaS Workforce / HRMS Full Product Completion
Sub-Phases A through I:
1. Employee Management & Organization Foundation
2. Attendance & Leave Workflows (Self-Service + Manager + HR)
3. Field Journeys (Start, Track, End, Approve)
4. Tasks & Day Planner Integration (Task -> Day Plan -> Finalize -> Complete)
5. KRA / Performance (Template, Assign, Submit, Manager Review & Approve)
6. Timesheet Workflows (Log Entry, Tag to Task, Manager Approve)
7. Workforce Dashboard & Live Summary Aggregation
8. Zero-Leakage Cross-Company Isolation Defense
9. Unentitled Tenant 403 Defense
10. Complete Clean Teardown
"""

import pytest
import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.main import app
from app.core.database import SessionLocal
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole, StaffDepartment
from app.models.staff_attendance import StaffAttendance
from app.models.staff_attendance_sheet import StaffLeaveType, StaffLeaveBalance, StaffLeaveRequest, StaffLeaveRequestDay, StaffLeaveApproval
from app.models.staff_journey import StaffJourney, StaffJourneyTrackPoint, JourneyStatus
from app.models.staff_tasks import StaffTask, StaffDayPlan, StaffDayPlanItem
from app.models.staff_kra import StaffKRATemplate, StaffKRAAssignment, StaffKRADailyInstance
from app.models.staff_timesheet import StaffTimesheetEntry

client = TestClient(app)

# Test Actor Constants
COMPANY_A_ID = 127  # Test Solar
COMPANY_B_ID = 94   # Apex Infotech
COMPANY_UNAUTH_ID = 92 # Test Company (No HRMS)

TESO_ADMIN_EMAIL = "teso_admin@testsolar.com"
APEX_ADMIN_EMAIL = "ananya.rao@apexinfotech.in"
RAMESH_UNAUTH_EMAIL = "ramesh@teco.zynova.cloud"


def get_token_for_email(email: str) -> str:
    db = SessionLocal()
    try:
        emp = db.query(StaffEmployee).filter_by(email=email).first()
        if not emp:
            raise ValueError(f"Actor with email {email} not found in DB")
        return SecurityManager.create_access_token({
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
        })
    finally:
        db.close()


@pytest.fixture(scope="module")
def tokens():
    return {
        "teso_admin": get_token_for_email(TESO_ADMIN_EMAIL),
        "apex_admin": get_token_for_email(APEX_ADMIN_EMAIL),
        "unauth_admin": get_token_for_email(RAMESH_UNAUTH_EMAIL),
    }


def test_01_tenant_admin_organization_foundation(tokens):
    """Test A: Tenant Admin retrieves company-scoped organization structure."""
    headers = {"Authorization": f"Bearer {tokens['teso_admin']}"}
    
    # 1. Departments (company-scoped)
    res_depts = client.get("/api/v1/staff/departments", headers=headers)
    assert res_depts.status_code == 200, res_depts.text
    data = res_depts.json()
    assert "departments" in data
    
    # 2. Designations (company-scoped + templates)
    res_desig = client.get("/api/v1/staff/designations", headers=headers)
    assert res_desig.status_code == 200, res_desig.text
    data_desig = res_desig.json()
    assert data_desig["success"] is True
    assert len(data_desig["designations"]) > 0
    names = [d["name"] for d in data_desig["designations"]]
    assert "Sales Executive" in names
    
    # 3. Roles
    res_roles = client.get("/api/v1/staff/roles", headers=headers)
    assert res_roles.status_code == 200, res_roles.text
    assert len(res_roles.json()["roles"]) > 0


def test_02_employee_management_lifecycle_and_hierarchy(tokens):
    """Test A/B: Tenant Admin provisions Manager and Employee with hierarchy, verifies profile & password reset."""
    headers = {"Authorization": f"Bearer {tokens['teso_admin']}"}
    db = SessionLocal()
    try:
        # Pre-cleanup in case of aborted runs
        db.execute(text("DELETE FROM staff_employees WHERE email IN ('e2e_mgr01@testsolar.com', 'e2e_emp01@testsolar.com')"))
        db.commit()

        # 1. Create Manager Employee
        mgr_payload = {
            "full_name": "E2E Manager",
            "first_name": "E2E",
            "last_name": "Manager",
            "email": "e2e_mgr01@testsolar.com",
            "phone": "9876543210",
            "role_id": 2,
            "designation": "Operations Manager",
            "date_of_joining": "2026-01-01",
            "assigned_modules": ["STAFF_HRMS"]
        }
        res_mgr = client.post("/api/v1/staff/employees", json=mgr_payload, headers=headers)
        assert res_mgr.status_code == 200, res_mgr.text
        mgr_id = res_mgr.json()["employee"]["id"]
        assert mgr_id > 0

        # 2. Create Staff Employee reporting to Manager
        staff_payload = {
            "full_name": "E2E Staff",
            "first_name": "E2E",
            "last_name": "Staff",
            "email": "e2e_emp01@testsolar.com",
            "phone": "9876543211",
            "role_id": 3,
            "designation": "Sales Executive",
            "reporting_manager_id": mgr_id,
            "date_of_joining": "2026-01-01",
            "assigned_modules": ["STAFF_HRMS"]
        }
        res_staff = client.post("/api/v1/staff/employees", json=staff_payload, headers=headers)
        assert res_staff.status_code == 200, res_staff.text
        staff_id = res_staff.json()["employee"]["id"]
        assert staff_id > 0

        # 3. Verify Employee Profile
        res_prof = client.get(f"/api/v1/staff/employees/{staff_id}", headers=headers)
        assert res_prof.status_code == 200
        emp_data = res_prof.json()["employee"]
        assert emp_data["email"] == "e2e_emp01@testsolar.com"
        assert emp_data["reporting_manager_id"] == mgr_id
        assert emp_data["designation"] == "Sales Executive"

        # 4. Admin Reset Password
        res_pwd = client.post(f"/api/v1/staff/employees/{staff_id}/reset-password", headers=headers)
        assert res_pwd.status_code == 200, res_pwd.text
        assert res_pwd.json()["success"] is True
    finally:
        db.close()


def test_03_attendance_workflow_self_and_manager(tokens):
    """Test B: Clock-in -> Today Status -> Clock-out -> History -> Manager Team Attendance."""
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # 1. Check status before clock in
    res_today = client.get("/api/v1/staff/attendance/today", headers=staff_headers)
    assert res_today.status_code == 200
    assert res_today.json()["status"] == "not_clocked_in"

    # 2. Clock-in
    clockin_payload = {
        "work_mode": "office",
        "location": {"latitude": 17.815743, "longitude": 83.205508, "accuracy": 10.0, "address": "Test Solar HQ"}
    }
    res_cin = client.post("/api/v1/staff/attendance/clock-in", json=clockin_payload, headers=staff_headers)
    assert res_cin.status_code == 200, res_cin.text
    assert res_cin.json()["success"] is True

    # 3. Check status is clocked_in
    res_cin_status = client.get("/api/v1/staff/attendance/today", headers=staff_headers)
    assert res_cin_status.status_code == 200
    assert res_cin_status.json()["status"] == "clocked_in"

    # 4. Clock-out
    clockout_payload = {
        "location": {"latitude": 17.815743, "longitude": 83.205508, "accuracy": 10.0}
    }
    res_cout = client.post("/api/v1/staff/attendance/clock-out", json=clockout_payload, headers=staff_headers)
    assert res_cout.status_code == 200, res_cout.text
    assert res_cout.json()["success"] is True

    # 5. History
    res_hist = client.get("/api/v1/staff/attendance/my-history", headers=staff_headers)
    assert res_hist.status_code == 200
    assert res_hist.json()["total"] >= 1

    # 6. Manager views team attendance
    res_team = client.get("/api/v1/staff/attendance/team", headers=mgr_headers)
    assert res_team.status_code == 200, res_team.text
    members = res_team.json().get("members", [])
    emp_ids = [m["id"] for m in members]
    assert staff_emp.id in emp_ids


def test_04_leave_workflow_apply_and_approve(tokens):
    """Test B: Leave Types -> Apply Leave -> Manager Approve -> HR/Admin Final Approve."""
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}
    admin_headers = {"Authorization": f"Bearer {tokens['teso_admin']}"}

    # 1. Leave Types
    res_types = client.get("/api/v1/staff/leaves/leave-types", headers=staff_headers)
    assert res_types.status_code == 200
    leave_types = res_types.json()["leave_types"]
    assert len(leave_types) > 0
    casual_type = next((lt for lt in leave_types if lt["code"] == "casual_leave"), leave_types[0])

    # 2. Staff applies for leave
    leave_date = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    apply_payload = {
        "leave_type_id": casual_type["id"],
        "reason": "Personal urgent work",
        "days": [{"leave_date": leave_date, "is_half_day": False}],
        "mark_as_lop": True
    }
    res_apply = client.post("/api/v1/staff/leaves/apply", json=apply_payload, headers=staff_headers)
    assert res_apply.status_code == 200, res_apply.text
    apply_data = res_apply.json()
    assert apply_data["success"] is True
    request_id = apply_data.get("leave_request_id") or apply_data.get("request_id")
    assert request_id > 0

    # 3. Manager views pending approvals
    res_mgr_appr = client.get("/api/v1/staff/leaves/pending-approvals/manager", headers=mgr_headers)
    assert res_mgr_appr.status_code == 200
    req_ids = [r["id"] for r in res_mgr_appr.json()["requests"]]
    assert request_id in req_ids

    # 4. Manager approves leave -> escalates to pending_hr
    res_mgr_dec = client.post(
        f"/api/v1/staff/leaves/approve/manager/{request_id}",
        json={"action": "approve", "remarks": "Approved by manager"},
        headers=mgr_headers
    )
    assert res_mgr_dec.status_code == 200, res_mgr_dec.text

    # 5. Tenant Admin views pending HR approvals
    res_hr_list = client.get("/api/v1/staff/leaves/pending-approvals/hr", headers=admin_headers)
    assert res_hr_list.status_code == 200
    hr_req_ids = [r["id"] for r in res_hr_list.json()["requests"]]
    assert request_id in hr_req_ids

    # 6. Tenant Admin approves HR leave -> status becomes approved
    res_hr_dec = client.post(
        f"/api/v1/staff/leaves/approve/hr/{request_id}",
        json={"action": "approve", "remarks": "Approved by HR"},
        headers=admin_headers
    )
    assert res_hr_dec.status_code == 200, res_hr_dec.text


def test_05_field_journey_workflow(tokens):
    """Test C: Start Journey -> Heartbeat -> End Journey -> Manager Approve."""
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    staff_headers = {"Authorization": f"Bearer {staff_token}", "User-Agent": mobile_ua}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}", "User-Agent": mobile_ua}

    # 1. Start Journey
    start_payload = {
        "purpose": "client_visit",
        "transport_mode": "bike",
        "start_latitude": 17.815743,
        "start_longitude": 83.205508,
        "start_odometer": 1000.0,
        "client_name": "Green Solar Farm",
        "client_address": "Sector 4 Industrial Area"
    }
    res_start = client.post("/api/v1/staff/journeys/start", json=start_payload, headers=staff_headers)
    assert res_start.status_code == 200, res_start.text
    journey_data = res_start.json()
    assert journey_data["success"] is True
    journey_id = journey_data["journey"]["id"]

    # 2. GPS Heartbeat
    hb_payload = {"location": {"latitude": 17.816000, "longitude": 83.205700, "speed": 15.0, "accuracy": 10.0}}
    res_hb = client.post(f"/api/v1/staff/journeys/{journey_id}/heartbeat", json=hb_payload, headers=staff_headers)
    assert res_hb.status_code == 200

    # 3. End Journey
    end_payload = {
        "location": {"latitude": 17.817000, "longitude": 83.206700, "accuracy": 10.0, "address": "Green Solar Site 1"},
        "notes": "Completed solar panel inspection"
    }
    res_end = client.post(f"/api/v1/staff/journeys/{journey_id}/end", json=end_payload, headers=staff_headers)
    assert res_end.status_code == 200, res_end.text
    assert res_end.json()["journey"]["status"] == "completed"

    # Reset journey timestamps and clean track points for deterministic WVV approval
    db = SessionLocal()
    j_rec = db.query(StaffJourney).filter_by(id=journey_id).first()
    start_t = datetime.datetime.now() - datetime.timedelta(minutes=30)
    end_t = datetime.datetime.now()
    j_rec.start_time = start_t
    j_rec.end_time = end_t
    j_rec.start_latitude = 17.815743
    j_rec.start_longitude = 83.205508
    j_rec.end_latitude = 17.816943
    j_rec.end_longitude = 83.206708
    j_rec.total_distance_km = 0.5

    # Remove any irregular points and add 6 clean sequential track points
    db.query(StaffJourneyTrackPoint).filter_by(journey_id=journey_id).delete()
    for i in range(6):
        tp = StaffJourneyTrackPoint(
            journey_id=journey_id,
            latitude=17.815743 + (i * 0.0002),
            longitude=83.205508 + (i * 0.0002),
            timestamp=start_t + datetime.timedelta(minutes=i * 5),
            speed_kmh=15.0,
            accuracy=15.0,
            wvv_compliant=True
        )
        db.add(tp)
    db.commit()
    db.close()

    # 4. Manager reviews and approves journey
    res_team = client.get("/api/v1/staff/journeys/team", headers=mgr_headers)
    assert res_team.status_code == 200
    team_j_ids = [j["id"] for j in res_team.json()["journeys"]]
    assert journey_id in team_j_ids

    res_appr = client.post(
        f"/api/v1/staff/journeys/{journey_id}/approve",
        json={"action": "approve", "remarks": "Route verified"},
        headers=mgr_headers
    )
    assert res_appr.status_code == 200, res_appr.text


def test_06_tasks_and_day_planner_integration(tokens):
    """Test D: Manager creates task -> Staff adds to Day Plan -> Finalize -> Task Completed."""
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # 1. Manager creates task
    task_payload = {
        "title": "Perform Solar Inverter Diagnostic",
        "description": "Run diagnostic scan on Inverter Unit #4",
        "category": "support",
        "priority": "high",
        "primary_assignee_id": staff_emp.id,
        "due_date": datetime.date.today().isoformat()
    }
    res_task = client.post("/api/v1/staff/tasks/", json=task_payload, headers=mgr_headers)
    assert res_task.status_code in (200, 201), res_task.text
    task_id = res_task.json()["task"]["id"]

    # 2. Staff views available tasks for Day Plan
    res_avail = client.get("/api/v1/staff/day-plans/available-tasks", headers=staff_headers)
    assert res_avail.status_code == 200
    avail_ids = [t["id"] for t in res_avail.json().get("tasks", [])]
    assert task_id in avail_ids

    # 3. Staff creates Day Plan with this task
    dp_payload = {
        "plan_date": datetime.date.today().isoformat(),
        "notes": "Plan for solar diagnostic",
        "items": [
            {
                "item_type": "task",
                "task_id": task_id,
                "title": "Perform Solar Inverter Diagnostic",
                "planned_status": "in_progress",
                "priority": "high"
            }
        ]
    }
    res_dp = client.post("/api/v1/staff/day-plans", json=dp_payload, headers=staff_headers)
    assert res_dp.status_code == 200, res_dp.text
    plan_data = res_dp.json()["plan"]
    assert len(plan_data["items"]) >= 1
    dp_item_id = plan_data["items"][0]["id"]

    # 4. Staff finalizes Day Plan and completes task
    finalize_payload = {
        "plan_date": datetime.date.today().isoformat(),
        "items": [
            {
                "item_id": dp_item_id,
                "eod_status": "completed",
                "eod_progress": 100,
                "eod_notes": "Diagnostic passed 100%",
                "time_spent_minutes": 90
            }
        ]
    }
    res_fin = client.post("/api/v1/staff/day-plans/finalize", json=finalize_payload, headers=staff_headers)
    assert res_fin.status_code == 200, res_fin.text

    # 5. Verify StaffTask is completed in database
    db = SessionLocal()
    task_in_db = db.query(StaffTask).filter_by(id=task_id).first()
    assert task_in_db.status == "completed"
    assert task_in_db.progress == 100
    db.close()


def test_07_kra_performance_workflow(tokens):
    """Test E: Tenant Admin creates KRA template -> Assigns to Staff -> Staff Submits -> Manager Approves."""
    headers_admin = {"Authorization": f"Bearer {tokens['teso_admin']}"}
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    # 1. Tenant Admin creates KRA Template
    kra_payload = {
        "title": "Solar Installation Turnaround Time",
        "description": "Complete site installation under 4 hours",
        "category": "operations",
        "frequency": "daily",
        "frequency_config": {"pattern": "daily"},
        "target_value": "4.0",
        "unit": "hours",
        "points_reward": 50,
        "is_active": True
    }
    res_kra = client.post("/api/v1/staff/kra/templates", json=kra_payload, headers=headers_admin)
    assert res_kra.status_code == 200, res_kra.text
    template_id = res_kra.json()["id"]

    # 2. Assign KRA template to Staff
    assign_payload = {
        "employee_ids": [staff_emp.emp_code],
        "reporting_manager_id": mgr_emp.id,
        "effective_from": datetime.date.today().isoformat()
    }
    res_assign = client.post(f"/api/v1/staff/kra/templates/{template_id}/assign", json=assign_payload, headers=headers_admin)
    assert res_assign.status_code == 200, res_assign.text

    # 3. Staff views "My KRAs" and submits achievement
    res_my_kras = client.get("/api/v1/staff/kra/my-kras", headers=staff_headers)
    assert res_my_kras.status_code == 200
    my_kras = res_my_kras.json().get("kras", [])
    assert len(my_kras) >= 1
    instance_id = my_kras[0]["id"]

    submit_payload = {
        "self_rating": 5,
        "self_remarks": "Completed installation in 3.5 hours",
        "time_spent_minutes": 210
    }
    res_sub = client.post(f"/api/v1/staff/kra/my-kras/{instance_id}/submit", json=submit_payload, headers=staff_headers)
    assert res_sub.status_code == 200, res_sub.text

    # 4. Manager reviews pending and approves
    res_pending = client.get("/api/v1/staff/kra/manager-review/pending", headers=mgr_headers)
    assert res_pending.status_code == 200
    pending_ids = [p["id"] for p in res_pending.json().get("pending_kras", [])]
    assert instance_id in pending_ids

    appr_payload = {
        "instance_id": instance_id,
        "notes": "Excellent speed and quality"
    }
    res_appr = client.post("/api/v1/staff/kra/manager-review/approve", json=appr_payload, headers=mgr_headers)
    assert res_appr.status_code == 200, res_appr.text


def test_08_timesheet_workflow(tokens):
    """Test F: Staff logs timesheet entry -> Tagged to Task -> Manager Approves."""
    db = SessionLocal()
    staff_emp = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    mgr_emp = db.query(StaffEmployee).filter_by(email="e2e_mgr01@testsolar.com").first()
    db.close()

    assert staff_emp is not None and mgr_emp is not None
    staff_token = get_token_for_email(staff_emp.email)
    mgr_token = get_token_for_email(mgr_emp.email)
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    today_str = datetime.date.today().isoformat()

    # 1. Staff logs timesheet entry
    ts_payload = {
        "date": today_str,
        "start_time": "14:00",
        "end_time": "16:00",
        "entry_type": "others",
        "comments": "Solar panel wiring and grounding inspection"
    }
    res_ts = client.post("/api/v1/staff/timesheet/", json=ts_payload, headers=staff_headers)
    assert res_ts.status_code == 200, res_ts.text
    ts_id = res_ts.json()["entry"]["id"]

    # 2. Staff views entries for date
    res_entries = client.get(f"/api/v1/staff/timesheet/my-entries/{today_str}", headers=staff_headers)
    assert res_entries.status_code == 200
    e_ids = [e["id"] for e in res_entries.json()["entries"]]
    assert ts_id in e_ids

    # 3. Manager views team entries for approval
    res_team_ts = client.get("/api/v1/staff/timesheet/team-entries", headers=mgr_headers)
    assert res_team_ts.status_code == 200
    team_ts_ids = [e["id"] for e in res_team_ts.json().get("entries", [])]
    assert ts_id in team_ts_ids

    # 4. Manager approves timesheet entry
    res_appr_ts = client.post(
        f"/api/v1/staff/timesheet/{ts_id}/approve",
        json={"action": "approve", "notes": "Hours verified"},
        headers=mgr_headers
    )
    assert res_appr_ts.status_code == 200, res_appr_ts.text


def test_09_workforce_dashboard_and_cockpit(tokens):
    """Test G: Workforce Dashboard aggregates live metrics across all modules."""
    headers_admin = {"Authorization": f"Bearer {tokens['teso_admin']}"}

    # 1. Workforce Summary (Cockpit Cards)
    res_sum = client.get("/api/v1/staff/workforce-summary", headers=headers_admin)
    assert res_sum.status_code == 200, res_sum.text
    data = res_sum.json()
    assert data["success"] is True
    assert data["company_id"] == COMPANY_A_ID
    assert data["total_employees"] >= 2
    assert "attendance" in data
    assert "present_today" in data["attendance"]
    assert "leave" in data
    assert "journeys" in data
    assert "tasks" in data
    assert "kra" in data
    assert "timesheet" in data

    # 2. Operations Overview (per employee grid)
    res_ov = client.get("/api/v1/staff/overview", headers=headers_admin)
    assert res_ov.status_code == 200, res_ov.text
    ov_data = res_ov.json()
    assert isinstance(ov_data, list)
    assert len(ov_data) >= 1


def test_10_cross_company_isolation_defense(tokens):
    """Test Isolation: Company B Admin (Apex) CANNOT access Company A data or approve Company A records."""
    headers_b = {"Authorization": f"Bearer {tokens['apex_admin']}"}
    db = SessionLocal()
    staff_a = db.query(StaffEmployee).filter_by(email="e2e_emp01@testsolar.com").first()
    db.close()

    assert staff_a is not None

    # 1. Company B Admin attempts to access Company A Staff Profile -> 403 Forbidden
    res_prof = client.get(f"/api/v1/staff/employees/{staff_a.id}", headers=headers_b)
    assert res_prof.status_code == 403, "Cross-company employee access must be blocked with 403"

    # 2. Company B Admin attempts to reset Company A Staff password -> 403 Forbidden
    res_pwd = client.post(f"/api/v1/staff/employees/{staff_a.id}/reset-password", headers=headers_b)
    assert res_pwd.status_code == 403

    # 3. Company B Admin views tasks -> ZERO Company A tasks visible
    res_tasks = client.get("/api/v1/staff/tasks/", headers=headers_b)
    assert res_tasks.status_code == 200
    for t in res_tasks.json().get("tasks", []):
        assert t.get("company_id") != COMPANY_A_ID


def test_11_unentitled_tenant_access_defense(tokens):
    """Test Entitlement: Tenant without STAFF_HRMS entitlement is strictly blocked (403) from all Workforce modules."""
    headers_unauth = {"Authorization": f"Bearer {tokens['unauth_admin']}"}

    # 1. Employee Provisioning (Requires STAFF_HRMS)
    unauth_emp_payload = {
        "full_name": "Unauth Test Staff",
        "first_name": "Unauth",
        "last_name": "Test",
        "role_id": 3,
        "date_of_joining": "2026-01-01"
    }
    res = client.post("/api/v1/staff/employees", json=unauth_emp_payload, headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 2. Attendance
    res = client.get("/api/v1/staff/attendance/today", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 3. Leave
    res = client.get("/api/v1/staff/leaves/leave-types", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 4. Journeys
    res = client.get("/api/v1/staff/journeys/my", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 5. Tasks
    res = client.get("/api/v1/staff/tasks/", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 6. Day Plans
    res = client.get("/api/v1/staff/day-plans/today", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 7. KRA
    res = client.get("/api/v1/staff/kra/my-kras", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 8. Timesheet
    res = client.get(f"/api/v1/staff/timesheet/my-entries/{datetime.date.today().isoformat()}", headers=headers_unauth)
    assert res.status_code == 403, res.text

    # 9. Workforce Summary
    res = client.get("/api/v1/staff/workforce-summary", headers=headers_unauth)
    assert res.status_code == 403, res.text


def test_12_clean_teardown():
    """Teardown: Safely and cleanly delete all manufactured test fixtures."""
    db = SessionLocal()
    try:
        # Find test employees
        test_emps = db.query(StaffEmployee).filter(StaffEmployee.email.in_(["e2e_mgr01@testsolar.com", "e2e_emp01@testsolar.com"])).all()
        emp_ids = [e.id for e in test_emps]

        if emp_ids:
            # Delete timesheets
            db.execute(text("DELETE FROM staff_timesheet_entries WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            # Delete day plans
            db.execute(text("DELETE FROM staff_day_plans WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            # Delete tasks
            db.execute(text("DELETE FROM staff_tasks WHERE primary_assignee_id IN :eids OR created_by IN :eids"), {"eids": tuple(emp_ids)})
            # Delete journeys
            db.execute(text("DELETE FROM staff_journeys WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            # Delete leave records
            db.execute(text("DELETE FROM staff_leave_requests WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            db.execute(text("DELETE FROM staff_leave_balances WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            # Delete attendance
            db.execute(text("DELETE FROM staff_attendance WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            # Delete KRA assignments & templates
            db.execute(text("DELETE FROM staff_kra_assignments WHERE employee_id IN :eids"), {"eids": tuple(emp_ids)})
            db.execute(text("DELETE FROM staff_kra_templates WHERE title = 'Solar Installation Turnaround Time'"))
            # Delete test employees
            db.execute(text("DELETE FROM staff_employees WHERE id IN :eids"), {"eids": tuple(emp_ids)})
            db.commit()
            print("Successfully and cleanly torn down all test records.")
    except Exception as e:
        db.rollback()
        print(f"Teardown error: {e}")
    finally:
        db.close()
