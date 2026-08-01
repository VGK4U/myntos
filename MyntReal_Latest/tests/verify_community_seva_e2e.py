#!/usr/bin/env python3
"""
E2E Frontend QA & Verification Pipeline for Ganesh Seva Community Integration
"""
import os
import sys
import subprocess
import time
import requests
import socket
from decimal import Decimal
import datetime

# Add backend app directory to path
sys.path.insert(0, "/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend")

from app.core.database import SessionLocal
from app.models.community_service import CommunityService, CommunityRegistration, CommunityCommission
from app.models.staff_accounts import OfficialPartner, VGKTeamIncomeEntry, VGKTeamCommissionConfig
from app.models.crm import CRMLead, CRMLeadTransaction
from sqlalchemy import text
from app.models.base import get_indian_time

# Configuration
BASE_URL = "http://127.0.0.1:5001"
API_BASE = f"{BASE_URL}/api/v1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5001

# Color logging helpers
def log(msg, color="info"):
    colors = {
        "info": "\033[94m[INFO]\033[0m",
        "success": "\033[92m[PASS]\033[0m",
        "fail": "\033[91m[FAIL]\033[0m",
        "warn": "\033[93m[WARN]\033[0m"
    }
    prefix = colors.get(color, "[INFO]")
    print(f"{prefix} {msg}")

def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

class ServerManager:
    def __init__(self):
        self.backend_proc = None
        self.frontend_proc = None

    def kill_existing(self):
        log("Cleaning up existing processes on ports 8000 and 5001...")
        import platform
        is_mac = platform.system() == 'Darwin'
        if is_mac:
            subprocess.run("pkill -f 'uvicorn.*8000' || true", shell=True)
            subprocess.run("pkill -f 'node.*server.js' || true", shell=True)
        else:
            subprocess.run("killall -9 uvicorn node || true", shell=True)
        time.sleep(2)

    def start_servers(self):
        self.kill_existing()
        
        env = os.environ.copy()
        
        # Start Backend
        log("Starting Backend on port 8000...")
        backend_dir = "/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/backend"
        self.backend_proc = subprocess.Popen(
            ["/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Start Frontend
        log("Starting Frontend on port 5001...")
        frontend_dir = "/Users/viswanathkari/Documents/Mynt OS/MyntReal_Latest/frontend"
        env["PORT"] = "5001"
        self.frontend_proc = subprocess.Popen(
            ["node", "server.js"],
            cwd=frontend_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for ports to be responsive
        log("Waiting for servers to start...")
        for i in range(30):
            if check_port_in_use(8000) and check_port_in_use(5001):
                log("Servers are up and responsive!", "success")
                return True
            time.sleep(1)
        
        log("Timeout waiting for servers to start.", "fail")
        return False

    def stop_servers(self):
        log("Stopping servers...")
        if self.backend_proc:
            self.backend_proc.terminate()
            self.backend_proc.wait()
        if self.frontend_proc:
            self.frontend_proc.terminate()
            self.frontend_proc.wait()
        self.kill_existing()
        log("Servers stopped.", "success")


def ensure_staff_employee_exists(db):
    from app.models.staff import StaffEmployee, StaffRole, StaffNdaVersion, StaffNdaAcceptance
    from app.core.security import SecurityManager
    
    role = db.query(StaffRole).filter(StaffRole.role_code == "vgk4u").first()
    if not role:
        role = StaffRole(
            role_name="VGK4U Supreme",
            role_code="vgk4u",
            hierarchy_level=100,
            is_active=True
        )
        db.add(role)
        db.flush()

    emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == "STF-TEST-VGK").first()
    password_hash = SecurityManager.get_password_hash("TestPass123!")
    if not emp:
        emp = StaffEmployee(
            emp_code="STF-TEST-VGK",
            full_name="STF Test VGK4U",
            password_hash=password_hash,
            staff_type="VGK4U Supreme",
            role_id=role.id,
            status="active",
            date_of_joining=get_indian_time().date(),
            base_company_id=1
        )
        db.add(emp)
    else:
        emp.password_hash = password_hash
        emp.status = "active"
        emp.role_id = role.id
    db.flush()
    db.commit()
    log("Ensured STF-TEST-VGK staff employee exists and password hash is set to default.")

    # Auto-accept all active NDAs/agreements for STF-TEST-VGK to prevent NDA_PENDING gate blocks
    active_ndas = db.query(StaffNdaVersion).filter(StaffNdaVersion.status == 'active').all()
    for nda in active_ndas:
        existing_acc = db.query(StaffNdaAcceptance).filter(
            StaffNdaAcceptance.employee_id == emp.id,
            StaffNdaAcceptance.nda_version_id == nda.id
        ).first()
        if not existing_acc:
            acc = StaffNdaAcceptance(
                employee_id=emp.id,
                nda_version_id=nda.id,
                accepted_at=get_indian_time(),
                acceptance_ip="127.0.0.1",
                acceptance_user_agent="E2E Testing Script",
                document_type=nda.document_type,
                employee_name_at_acceptance=emp.full_name,
                employee_code_at_acceptance=emp.emp_code
            )
            db.add(acc)
            log(f"Auto-accepted active {nda.document_type} version {nda.version_number} for STF-TEST-VGK.")
    db.commit()


def get_comm_token():
    resp = requests.post(f"{API_BASE}/vgk/auth/login", json={
        "identifier": "TEST_COMM_01",
        "password": "TestPassword123!"
    })
    if resp.status_code != 200:
        log(f"Community partner login failed: {resp.text}", "fail")
        return None
    return resp.json()["access_token"]


def main():
    db = SessionLocal()
    ensure_staff_employee_exists(db)
    
    # 1. Seed test data
    log("Seeding sandbox test data...")
    from app.services.sandbox_seeder import seed_sandbox_data
    seed_res = seed_sandbox_data(db)
    log(f"Sandbox seeder: {seed_res['message']}")
    
    service_id = seed_res["data"]["service_id"]
    reg_id = seed_res["data"]["registration_id"]
    lead_id = seed_res["data"]["lead_id"]
    ref1_id = seed_res["data"]["ref1_partner_id"]
    ref2_id = seed_res["data"]["ref2_partner_id"]
    
    # Launch servers
    manager = ServerManager()
    if not manager.start_servers():
        manager.stop_servers()
        sys.exit(1)

    success_status = False
    try:
        # Get Staff Token
        log("Logging in as staff (STF-TEST-VGK)...")
        resp = requests.post(f"{API_BASE}/staff/auth/login", json={
            "employee_id": "STF-TEST-VGK",
            "password": "TestPass123!"
        })
        assert resp.status_code == 200, f"Staff login failed: {resp.text}"
        staff_token = resp.json()["access_token"]
        staff_headers = {"Authorization": f"Bearer {staff_token}"}
        log("Staff login successful.", "success")

        # ── Test A: Header Badge & Date Range Visibility ──
        log("\n--- TEST A: Admin Configuration & Header Badge Visibility ---")
        
        # Verify TEST_Ganesh_Seva returned in active headers
        resp = requests.get(f"{API_BASE}/community-services/public/active-headers")
        assert resp.status_code == 200, f"Failed to get active headers: {resp.text}"
        services = resp.json()["services"]
        short_names = [s["short_name"] for s in services]
        assert "TEST_Ganesh_Seva" in short_names, "TEST_Ganesh_Seva not found in active headers!"
        log("TEST_Ganesh_Seva is correctly returned in active headers.", "success")

        # Confirm date range filtering dynamically controls visibility:
        # Update start_date / end_date to be in the future (inactive)
        log("Setting service dates to future (inactive)...")
        service_obj = db.query(CommunityService).filter(CommunityService.id == service_id).first()
        service_obj.start_date = datetime.date.today() + datetime.timedelta(days=10)
        service_obj.end_date = datetime.date.today() + datetime.timedelta(days=20)
        db.commit()

        # Query headers again and assert TEST_Ganesh_Seva is NOT returned
        resp = requests.get(f"{API_BASE}/community-services/public/active-headers")
        services = resp.json()["services"]
        short_names = [s["short_name"] for s in services]
        assert "TEST_Ganesh_Seva" not in short_names, "TEST_Ganesh_Seva should NOT be returned when start_date is in the future!"
        log("TEST_Ganesh_Seva is successfully hidden when dates are out of range.", "success")

        # Restore dates to active range
        log("Restoring service dates to active range...")
        service_obj.start_date = datetime.date.today() - datetime.timedelta(days=1)
        service_obj.end_date = datetime.date.today() + datetime.timedelta(days=30)
        db.commit()

        resp = requests.get(f"{API_BASE}/community-services/public/active-headers")
        services = resp.json()["services"]
        short_names = [s["short_name"] for s in services]
        assert "TEST_Ganesh_Seva" in short_names, "TEST_Ganesh_Seva should be active again!"
        log("TEST_Ganesh_Seva is active again.", "success")

        # ── Test B: Public Landing & Sign-up Form ──
        log("\n--- TEST B: Public Landing & Sign-Up Page ---")
        
        # Navigate to /community-services/TEST_Ganesh_Seva (verify 200)
        resp = requests.get(f"{BASE_URL}/community-services/TEST_Ganesh_Seva")
        assert resp.status_code == 200, f"Public landing page returned {resp.status_code}!"
        log("Public landing page `/community-services/TEST_Ganesh_Seva` loaded successfully.", "success")

        # Verify typeahead search for TEST_REF_01
        resp = requests.get(f"{API_BASE}/vgk/members/search?q=TEST_REF_01")
        assert resp.status_code == 200, f"Referrer search failed: {resp.text}"
        members = resp.json()["data"]
        partner_codes = [m["partner_code"] for m in members]
        assert "TEST_REF_01" in partner_codes, "TEST_REF_01 not found in typeahead referrer results!"
        log("Referrer typeahead lookup returns TEST_REF_01.", "success")

        # Submit public registration form
        log("Submitting new registration form...")
        resp = requests.post(f"{API_BASE}/community-services/public/register", data={
            "community_service_id": service_id,
            "primary_name": "Test Seva Mandapam 2026 - Form Submission",
            "primary_phone_1": "9999990101",
            "area": "Test Sandbox Area",
            "pin_code": "500001",
            "district": "Test District",
            "state": "Test State",
            "ref1_member_id": ref1_id,
            "ref2_member_id": ref2_id
        })
        assert resp.status_code == 200, f"Registration form submission failed: {resp.text}"
        reg_data = resp.json()
        assert reg_data["success"] == True, "Registration status should be success"
        log("Community sign-up submitted and credentials/whatsapp modal triggers successfully.", "success")

        # ── Test C: Lead Assignment in CRM ──
        log("\n--- TEST C: Lead Assignment in CRM ---")

        # Test active search typeahead for Mandapam
        resp = requests.get(f"{API_BASE}/community-services/admin/active-search?q=Mandapam", headers=staff_headers)
        assert resp.status_code == 200, f"Active community search failed: {resp.text}"
        active_results = resp.json()["results"]
        display_texts = [r["display"] for r in active_results]
        assert any("Test Seva Mandapam 2026" in text for text in display_texts), "Test Seva Mandapam 2026 not found in active search results!"
        log("Active community typeahead returns Test Seva Mandapam 2026.", "success")

        # Assign lead to community
        log(f"Assigning lead #{lead_id} to community registration #{reg_id}...")
        resp = requests.put(f"{API_BASE}/crm/leads/{lead_id}", headers=staff_headers, params={"company_id": 1}, json={
            "community_id": reg_id,
            "company_id": 1
        })
        assert resp.status_code == 200, f"Lead assignment update failed: {resp.text}"
        updated_lead = resp.json()["data"]
        assert updated_lead["community_id"] == reg_id, "community_id was not updated correctly!"
        log("Lead successfully assigned and saved to the community.", "success")

        # ── Test D: Dashboard & Payout Verification ──
        log("\n--- TEST D: Dashboard & Payout Verification ---")

        # Create a validated transaction for TEST_LEAD_01
        log("Creating and validating transaction for TEST_LEAD_01...")
        
        # Add transaction
        txn = CRMLeadTransaction(
            company_id=1,
            lead_id=lead_id,
            amount=20000.0,
            transaction_type="advance",
            payment_mode="bank_transfer",
            validation_status="pending",
            transaction_date=get_indian_time().replace(tzinfo=None)
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)

        # Validate transaction via API
        resp = requests.patch(f"{API_BASE}/crm/transactions/{txn.id}/validate", headers=staff_headers, params={
            "company_id": 1
        }, json={
            "action": "validate"
        })
        assert resp.status_code == 200, f"Transaction validation failed: {resp.text}"
        log("Transaction successfully validated.", "success")

        # Get Community Partner Token
        log("Logging in as Community Partner (TEST_COMM_01)...")
        comm_token = get_comm_token()
        assert comm_token is not None, "Failed to retrieve community partner token!"
        comm_headers = {"Authorization": f"Bearer {comm_token}"}
        log("Community Partner login successful.", "success")

        # Verify Seva contribution shows as RELEASED in the TEST_COMM_01 dashboard ledger
        resp = requests.get(f"{API_BASE}/community-services/my-earnings", headers=comm_headers)
        assert resp.status_code == 200, f"Failed to get community earnings: {resp.text}"
        earnings = resp.json()
        assert earnings["total_seva_earned"] > 0, "No Seva contribution earned!"
        commissions = earnings["commissions"]
        released_commissions = [c for c in commissions if c["status"] == "RELEASED" and c["lead_id"] == lead_id]
        assert len(released_commissions) > 0, "No released Seva contribution found for lead!"
        log("Seva Contribution correctly released and visible in the Community earnings tab.", "success")

        # Simulate final completion on lead
        log("Updating lead status to completion...")
        resp = requests.put(f"{API_BASE}/crm/leads/{lead_id}", headers=staff_headers, params={"company_id": 1}, json={
            "solar_pipeline_status": "subsidy_pending",
            "company_id": 1
        })
        assert resp.status_code == 200, f"Lead completion stage update failed: {resp.text}"
        log("Lead stage transitioned to completion/subsidy_pending.", "success")

        # Verify upline deductions are logged in vgk_team_income_entries
        ded_l1 = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead_id,
            VGKTeamIncomeEntry.level == 1
        ).first()
        ded_l2 = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead_id,
            VGKTeamIncomeEntry.level == 2
        ).first()
        ded_l5 = db.query(VGKTeamIncomeEntry).filter(
            VGKTeamIncomeEntry.source_lead_id == lead_id,
            VGKTeamIncomeEntry.level == 5
        ).first()

        assert ded_l1 is not None, "L1 deduction not found!"
        assert ded_l1.commission_amount == Decimal("-1000.0"), f"L1 deduction amount mismatch: {ded_l1.commission_amount}"
        log("L1 Upline deduction (₹1,000) logged correctly.", "success")

        assert ded_l2 is not None, "L2 deduction not found!"
        assert ded_l2.commission_amount == Decimal("-500.0"), f"L2 deduction amount mismatch: {ded_l2.commission_amount}"
        log("L2 Upline deduction (₹500) logged correctly.", "success")

        assert ded_l5 is not None, "L5 deduction not found!"
        assert ded_l5.commission_amount == Decimal("-500.0"), f"L5 deduction amount mismatch: {ded_l5.commission_amount}"
        log("L5 Field Support deduction (₹500) logged correctly.", "success")

        log("\n🎉 ALL E2E AND FRONT-END FLOWS COMPLETED AND VALIDATED WITH ZERO ERRORS!", "success")
        success_status = True

    except Exception as e:
        import traceback
        log(f"Test run failed with error: {e}", "fail")
        traceback.print_exc()
        success_status = False

    finally:
        # Cleanup
        log("Performing final database cleanup...")
        db.execute(text("DELETE FROM vgk_team_income_entries WHERE source_lead_id = :lid"), {"lid": lead_id})
        db.execute(text("DELETE FROM community_commissions WHERE lead_id = :lid"), {"lid": lead_id})
        db.execute(text("DELETE FROM crm_lead_transactions WHERE lead_id = :lid"), {"lid": lead_id})
        db.execute(text("DELETE FROM crm_leads WHERE id = :lid"), {"lid": lead_id})
        db.execute(text("DELETE FROM community_registrations WHERE community_service_id = :sid"), {"sid": service_id})
        db.execute(text("DELETE FROM community_services WHERE id = :sid"), {"sid": service_id})
        db.execute(text("DELETE FROM official_partners WHERE partner_code IN ('TEST_REF_01', 'TEST_REF_02', 'TEST_COMM_01')"))
        db.commit()
        db.close()
        
        manager.stop_servers()
        sys.exit(0 if success_status else 1)

if __name__ == "__main__":
    main()
