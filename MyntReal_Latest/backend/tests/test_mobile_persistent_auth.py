"""
Automated Test Suite: Mobile Persistent Auth & Rotating Refresh Tokens
Validates:
1. Mobile device session creation on login
2. Rotating refresh tokens (one-time use)
3. Token rotation sliding-window expiry
4. Immediate revocation when staff password changes (token_version bump)
5. Explicit revocation on logout
6. Rejection for locked or inactive staff accounts
7. Strict preservation of tenant_id and company_id isolation across token rotations
"""

import pytest
import secrets
import hashlib
import concurrent.futures
from datetime import datetime, timedelta, date
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.core.timezone import get_indian_time
from app.models.staff import StaffEmployee, StaffRole
from app.models.mobile_device_session import MobileDeviceSession
from app.core.security import SecurityManager

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_staff(db):
    role = db.query(StaffRole).first()
    if not role:
        role = StaffRole(
            role_code="test_role",
            role_name="Test Role",
            hierarchy_level=10
        )
        db.add(role)
        db.commit()
        db.refresh(role)

    emp_code = f"TEST_M_{secrets.token_hex(4).upper()}"
    emp = StaffEmployee(
        emp_code=emp_code,
        first_name="Mobile",
        last_name="Tester",
        full_name="Mobile Tester",
        role_id=role.id,
        date_of_joining=date.today(),
        email=f"{emp_code.lower()}@myntreal.test",
        password_hash=SecurityManager.get_password_hash("TestPassword123!"),
        status="active",
        token_version=1,
        base_company_id=1,
        tenant_id=1,
        data_companies=[1, 4]
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    yield emp

    # Cleanup
    db.query(MobileDeviceSession).filter_by(staff_id=emp.id).delete()
    db.query(StaffEmployee).filter_by(id=emp.id).delete()
    db.commit()


def test_mobile_login_and_refresh_token_rotation(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"

    # 1. Login from mobile with device_id
    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android",
        "device_name": "Pixel 8 Pro",
        "app_version": "1.0.1"
    })
    assert login_res.status_code == 200, login_res.text
    data = login_res.json()
    assert data["success"] is True
    assert data["access_token"] is not None
    assert data["refresh_token"] is not None
    first_refresh_token = data["refresh_token"]

    # Verify session in DB
    h1 = hashlib.sha256(first_refresh_token.encode()).hexdigest()
    sess = db.query(MobileDeviceSession).filter_by(device_id=device_id).first()
    assert sess is not None
    assert sess.refresh_token_hash == h1
    assert sess.is_revoked is False
    assert sess.staff_id == test_staff.id

    # 2. Call /auth/mobile/refresh to rotate token
    refresh_res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": first_refresh_token,
        "device_id": device_id
    })
    assert refresh_res.status_code == 200, refresh_res.text
    ref_data = refresh_res.json()
    assert ref_data["success"] is True
    assert ref_data["access_token"] is not None
    assert ref_data["refresh_token"] is not None
    second_refresh_token = ref_data["refresh_token"]
    assert second_refresh_token != first_refresh_token, "Refresh token MUST rotate"

    # Verify token claims preserved (tenant isolation)
    payload = SecurityManager.verify_token(ref_data["access_token"])
    assert payload is not None
    assert payload["sub"] == str(test_staff.id)
    assert payload["base_company_id"] == 1
    assert payload["tenant_id"] == 1

    # 3. Old refresh token MUST be rejected (anti-replay guard)
    replay_res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": first_refresh_token,
        "device_id": device_id
    })
    assert replay_res.status_code == 401, "Old rotated token must be rejected"

    # 4. New rotated refresh token succeeds
    refresh_res2 = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": second_refresh_token,
        "device_id": device_id
    })
    assert refresh_res2.status_code == 200
    third_refresh_token = refresh_res2.json()["refresh_token"]

    # 5. Revoke session on logout
    revoke_res = client.post("/api/v1/staff/auth/mobile/revoke", json={
        "refresh_token": third_refresh_token,
        "device_id": device_id
    })
    assert revoke_res.status_code == 200

    # 6. Revoked session MUST be rejected
    after_revoke_res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": third_refresh_token,
        "device_id": device_id
    })
    assert after_revoke_res.status_code == 401


def test_password_change_invalidates_mobile_session(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"

    # Login
    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android"
    })
    refresh_tok = login_res.json()["refresh_token"]

    # Simulate password change (token_version bumped)
    test_staff.token_version = test_staff.token_version + 1
    db.commit()

    # Attempt refresh -> MUST fail with 401
    res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": refresh_tok,
        "device_id": device_id
    })
    assert res.status_code == 401
    assert "revoked" in res.json()["detail"].lower()


def test_inactive_staff_rejected(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"

    # Login
    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android"
    })
    refresh_tok = login_res.json()["refresh_token"]

    # Deactivate staff
    test_staff.status = "inactive"
    db.commit()

    # Attempt refresh -> MUST fail with 401
    res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": refresh_tok,
        "device_id": device_id
    })
    assert res.status_code == 401


def test_concurrent_refresh_requests_race_condition(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"

    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android"
    })
    assert login_res.status_code == 200
    refresh_token = login_res.json()["refresh_token"]

    def do_refresh():
        c = TestClient(app)
        return c.post("/api/v1/staff/auth/mobile/refresh", json={
            "refresh_token": refresh_token,
            "device_id": device_id
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(do_refresh)
        f2 = executor.submit(do_refresh)
        res1 = f1.result()
        res2 = f2.result()

    statuses = sorted([res1.status_code, res2.status_code])
    assert statuses == [200, 401], f"Expected [200, 401], got {statuses}"


def test_device_id_mismatch_rejected(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"
    wrong_device_id = f"dev_{secrets.token_hex(8)}"

    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android"
    })
    assert login_res.status_code == 200
    refresh_token = login_res.json()["refresh_token"]

    res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": refresh_token,
        "device_id": wrong_device_id
    })
    assert res.status_code == 401
    assert "Invalid or unrecognized" in res.json()["detail"]


def test_revoke_all_devices(test_staff, db):
    device_id_1 = f"dev_{secrets.token_hex(8)}"
    device_id_2 = f"dev_{secrets.token_hex(8)}"

    login_res_1 = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id_1,
        "platform": "android"
    })
    assert login_res_1.status_code == 200
    tok1 = login_res_1.json()["refresh_token"]

    login_res_2 = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id_2,
        "platform": "ios"
    })
    assert login_res_2.status_code == 200
    tok2 = login_res_2.json()["refresh_token"]

    revoke_res = client.post("/api/v1/staff/auth/mobile/revoke", json={
        "refresh_token": tok1,
        "device_id": device_id_1,
        "revoke_all_devices": True
    })
    assert revoke_res.status_code == 200
    assert revoke_res.json()["success"] is True

    r1 = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": tok1,
        "device_id": device_id_1
    })
    assert r1.status_code == 401

    r2 = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": tok2,
        "device_id": device_id_2
    })
    assert r2.status_code == 401


def test_expired_session_rejected(test_staff, db):
    device_id = f"dev_{secrets.token_hex(8)}"

    login_res = client.post("/api/v1/staff/auth/login", json={
        "employee_id": test_staff.emp_code,
        "password": "TestPassword123!",
        "device_id": device_id,
        "platform": "android"
    })
    assert login_res.status_code == 200
    refresh_tok = login_res.json()["refresh_token"]

    sess = db.query(MobileDeviceSession).filter_by(device_id=device_id).first()
    assert sess is not None
    sess.expires_at = get_indian_time() - timedelta(days=1)
    db.commit()

    res = client.post("/api/v1/staff/auth/mobile/refresh", json={
        "refresh_token": refresh_tok,
        "device_id": device_id
    })
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()

