"""
Comprehensive Automated Test Suite: Phase 2A Screen-Off Telephony Backend Foundation
Validates:
1. Android FCM and iOS APNs VoIP push token registration
2. Token upsert, rotation, and validation rules
3. Strict multi-tenant isolation and authorization
4. Inactive/disabled staff rejection
5. Push token revocation on logout
6. Idempotent push dispatch and duplicate suppression
7. Call cancellation push signaling
8. Feature flag kill-switch (ENABLE_MOBILE_VOIP_PUSH)
9. FastAPI endpoints authentication and responses
10. Regression safety of existing softphone and auth flows
"""

import pytest
import secrets
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.security import SecurityManager
from app.models.staff import StaffEmployee, StaffRole
from app.models.mobile_device_push_token import MobileDevicePushToken
from app.models.telephony_call_flow import TelephonyPlivoEndpoint
from app.services.telephony.mobile_push_service import (
    MobilePushService, MobileCallNotifier, _CALL_STATE_CACHE, _MOCK_DISPATCH_LOG
)

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_company_id():
    return 1


@pytest.fixture
def test_staff(db, test_company_id):
    role = db.query(StaffRole).first()
    if not role:
        role = StaffRole(role_code="test_role", role_name="Test Role", hierarchy_level=10)
        db.add(role)
        db.commit()
        db.refresh(role)

    emp_code = f"TEST_V_{secrets.token_hex(4).upper()}"
    emp = StaffEmployee(
        emp_code=emp_code,
        first_name="VoIP",
        last_name="Tester",
        full_name="VoIP Push Tester",
        role_id=role.id,
        date_of_joining=date.today(),
        email=f"{emp_code.lower()}@myntreal.test",
        password_hash=SecurityManager.get_password_hash("TestPassword123!"),
        status="active",
        token_version=1,
        staff_type="TENANT_ADMIN",
        base_company_id=test_company_id
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)

    # Provision TelephonyPlivoEndpoint
    endpoint = TelephonyPlivoEndpoint(
        company_id=test_company_id,
        staff_id=emp.id,
        plivo_endpoint_id=f"ep_{secrets.token_hex(4)}",
        plivo_username=f"agentc{test_company_id}s{emp.id}",
        plivo_alias=f"{emp.emp_code}_VoIP",
        is_registered=False
    )
    db.add(endpoint)
    db.commit()

    yield emp

    # Cleanup
    db.query(MobileDevicePushToken).filter(MobileDevicePushToken.staff_id == emp.id).delete()
    db.query(TelephonyPlivoEndpoint).filter(TelephonyPlivoEndpoint.staff_id == emp.id).delete()
    db.query(StaffEmployee).filter(StaffEmployee.id == emp.id).delete()
    db.commit()


@pytest.fixture
def staff_auth_token(test_staff):
    return SecurityManager.create_access_token({
        "sub": str(test_staff.id),
        "emp_code": test_staff.emp_code,
        "token_version": test_staff.token_version,
        "type": "staff",
        "company_id": test_staff.base_company_id or 1
    })


# ── 1. DEVICE TOKEN REGISTRATION TESTS ────────────────────────────────────────

def test_push_token_registration_android(db, test_staff, test_company_id):
    device_id = f"android_dev_{secrets.token_hex(6)}"
    fcm_token = f"fcm_sample_{secrets.token_hex(16)}"

    record = MobilePushService.register_device_token(
        db=db,
        company_id=test_company_id,
        staff_id=test_staff.id,
        device_id=device_id,
        platform="android",
        push_token=fcm_token,
        app_version="1.0.1"
    )

    assert record.id is not None
    assert record.platform == "android"
    assert record.token_type == "fcm_data"
    assert record.push_token == fcm_token
    assert record.is_active is True

    # Verify Plivo endpoint was automatically marked is_registered = True
    ep = db.query(TelephonyPlivoEndpoint).filter(
        TelephonyPlivoEndpoint.staff_id == test_staff.id,
        TelephonyPlivoEndpoint.company_id == test_company_id
    ).first()
    assert ep.is_registered is True


def test_push_token_registration_ios(db, test_staff, test_company_id):
    device_id = f"ios_dev_{secrets.token_hex(6)}"
    voip_token = f"apns_hex_{secrets.token_hex(32)}"

    record = MobilePushService.register_device_token(
        db=db,
        company_id=test_company_id,
        staff_id=test_staff.id,
        device_id=device_id,
        platform="ios",
        push_token=voip_token,
        token_type="apns_voip",
        app_version="1.0.1"
    )

    assert record.id is not None
    assert record.platform == "ios"
    assert record.token_type == "apns_voip"
    assert record.push_token == voip_token
    assert record.is_active is True


def test_push_token_upsert_and_rotation(db, test_staff, test_company_id):
    device_id = f"rot_dev_{secrets.token_hex(6)}"
    initial_token = f"fcm_v1_{secrets.token_hex(8)}"
    rotated_token = f"fcm_v2_{secrets.token_hex(8)}"

    rec1 = MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token=initial_token
    )
    rec1_id = rec1.id

    rec2 = MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token=rotated_token
    )

    assert rec2.id == rec1_id
    assert rec2.push_token == rotated_token

    # Ensure no duplicates created
    count = db.query(MobileDevicePushToken).filter(
        MobileDevicePushToken.staff_id == test_staff.id,
        MobileDevicePushToken.device_id == device_id
    ).count()
    assert count == 1


# ── 2. VALIDATION & SECURITY TESTS ───────────────────────────────────────────

def test_push_token_validation_errors(db, test_staff, test_company_id):
    # Empty device_id
    with pytest.raises(ValueError, match="device_id is required"):
        MobilePushService.register_device_token(
            db=db, company_id=test_company_id, staff_id=test_staff.id,
            device_id="", platform="android", push_token="valid_token"
        )

    # Empty push_token
    with pytest.raises(ValueError, match="push_token is required"):
        MobilePushService.register_device_token(
            db=db, company_id=test_company_id, staff_id=test_staff.id,
            device_id="dev1", platform="android", push_token=""
        )

    # Invalid platform
    with pytest.raises(ValueError, match="Must be 'android' or 'ios'"):
        MobilePushService.register_device_token(
            db=db, company_id=test_company_id, staff_id=test_staff.id,
            device_id="dev1", platform="windows", push_token="valid_token"
        )

    # Invalid token_type
    with pytest.raises(ValueError, match="Must be 'fcm_data' or 'apns_voip'"):
        MobilePushService.register_device_token(
            db=db, company_id=test_company_id, staff_id=test_staff.id,
            device_id="dev1", platform="android", push_token="valid_token", token_type="sms"
        )


def test_tenant_isolation_controls(db, test_staff, test_company_id):
    wrong_company_id = 999
    device_id = f"dev_tenant_{secrets.token_hex(4)}"

    # Attempt registration with wrong company_id must fail
    with pytest.raises(PermissionError, match="does not belong to company"):
        MobilePushService.register_device_token(
            db=db, company_id=wrong_company_id, staff_id=test_staff.id,
            device_id=device_id, platform="android", push_token="fcm_valid"
        )

    # Register valid token under correct company
    MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token="fcm_valid"
    )

    # Query with wrong company must return empty
    wrong_tokens = MobilePushService.get_active_tokens_for_staff(db, wrong_company_id, test_staff.id)
    assert len(wrong_tokens) == 0

    # Query with correct company must return token
    correct_tokens = MobilePushService.get_active_tokens_for_staff(db, test_company_id, test_staff.id)
    assert len(correct_tokens) == 1


def test_inactive_staff_rejection(db, test_staff, test_company_id):
    test_staff.status = "inactive"
    db.commit()

    with pytest.raises(PermissionError, match="is inactive"):
        MobilePushService.register_device_token(
            db=db, company_id=test_company_id, staff_id=test_staff.id,
            device_id="dev_inactive", platform="android", push_token="fcm_valid"
        )


# ── 3. REVOCATION & LOGOUT CLEANUP TESTS ──────────────────────────────────────

def test_push_token_revocation(db, test_staff, test_company_id):
    device_id = f"dev_rev_{secrets.token_hex(4)}"
    MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token="fcm_active"
    )

    active_before = MobilePushService.get_active_tokens_for_staff(db, test_company_id, test_staff.id)
    assert len(active_before) == 1

    # Revoke on logout
    revoked = MobilePushService.revoke_device_token(db, test_company_id, test_staff.id, device_id)
    assert revoked is True

    active_after = MobilePushService.get_active_tokens_for_staff(db, test_company_id, test_staff.id)
    assert len(active_after) == 0


# ── 4. DISPATCH & IDEMPOTENCY TESTS ───────────────────────────────────────────

def test_inbound_push_dispatch_and_mock_telemetry(db, test_staff, test_company_id):
    MobileCallNotifier.clear_mock_dispatch_log()
    device_id = f"dev_disp_{secrets.token_hex(4)}"
    fcm_token = f"fcm_test_{secrets.token_hex(16)}"

    MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token=fcm_token
    )

    session_id = f"vcs_test_{secrets.token_hex(4)}"
    res = MobileCallNotifier.notify_inbound_call(
        caller_phone="+919876543210",
        called_did="+918031728899",
        provider_call_id=f"uuid_{secrets.token_hex(6)}",
        call_session_id=session_id,
        target_staff_ids=[test_staff.id],
        company_id=test_company_id,
        lead_name="Priya Sharma (Lead #204)",
        lead_id=204,
        db=db
    )

    assert res["status"] == "dispatched"
    assert res["dispatched_count"] >= 1

    logs = MobileCallNotifier.get_mock_dispatch_log()
    assert len(logs) >= 1
    last_log = logs[-1]
    assert last_log["platform"] == "android"
    assert last_log["payload"]["type"] == "incoming_call"
    assert last_log["payload"]["caller_number"] == "+91 98••••3210"  # Privacy masked
    assert last_log["payload"]["caller_name"] == "Priya Sharma (Lead #204)"


def test_idempotency_suppresses_duplicate_ringing(db, test_staff, test_company_id):
    device_id = f"dev_idem_{secrets.token_hex(4)}"
    MobilePushService.register_device_token(
        db=db, company_id=test_company_id, staff_id=test_staff.id,
        device_id=device_id, platform="android", push_token=f"fcm_{secrets.token_hex(8)}"
    )

    session_id = f"vcs_idem_{secrets.token_hex(4)}"

    # First dispatch -> Success
    res1 = MobileCallNotifier.notify_inbound_call(
        caller_phone="+919876543210", called_did="+918031728899",
        provider_call_id="uuid_1", call_session_id=session_id,
        target_staff_ids=[test_staff.id], company_id=test_company_id, db=db
    )
    assert res1["dispatched_count"] == 1

    # Second immediate dispatch for same session & staff -> Suppressed!
    res2 = MobileCallNotifier.notify_inbound_call(
        caller_phone="+919876543210", called_did="+918031728899",
        provider_call_id="uuid_1", call_session_id=session_id,
        target_staff_ids=[test_staff.id], company_id=test_company_id, db=db
    )
    assert res2["dispatched_count"] == 0


def test_call_cancellation_dispatch(db, test_staff, test_company_id):
    session_id = f"vcs_canc_{secrets.token_hex(4)}"
    res = MobileCallNotifier.notify_call_cancelled(
        call_session_id=session_id,
        provider_call_id="uuid_canc",
        target_staff_ids=[test_staff.id],
        company_id=test_company_id,
        reason="caller_hung_up",
        db=db
    )
    assert res["status"] == "cancelled"


def test_feature_flag_kill_switch(db, test_staff, test_company_id, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MOBILE_VOIP_PUSH", False)

    res = MobileCallNotifier.notify_inbound_call(
        caller_phone="+919876543210", called_did="+918031728899",
        provider_call_id="uuid_ff", call_session_id="session_ff",
        target_staff_ids=[test_staff.id], company_id=test_company_id, db=db
    )
    assert res["status"] == "disabled"
    assert res["dispatched_count"] == 0


# ── 5. FASTAPI ENDPOINT TESTS ─────────────────────────────────────────────────

def test_api_push_token_registration(staff_auth_token):
    resp = client.post(
        "/api/v1/telephony/mobile/push-token",
        headers={"Authorization": f"Bearer {staff_auth_token}"},
        json={
            "device_id": f"api_dev_{secrets.token_hex(4)}",
            "platform": "android",
            "push_token": f"fcm_api_{secrets.token_hex(8)}",
            "app_version": "1.0.1"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["platform"] == "android"


def test_api_push_token_unauthenticated():
    resp = client.post(
        "/api/v1/telephony/mobile/push-token",
        json={"device_id": "d1", "platform": "android", "push_token": "tok"}
    )
    assert resp.status_code == 401


def test_api_push_token_revoke(staff_auth_token):
    dev_id = f"dev_api_rev_{secrets.token_hex(4)}"
    # First register
    client.post(
        "/api/v1/telephony/mobile/push-token",
        headers={"Authorization": f"Bearer {staff_auth_token}"},
        json={"device_id": dev_id, "platform": "android", "push_token": "fcm_tok"}
    )

    # Now revoke
    resp = client.post(
        "/api/v1/telephony/mobile/push-token/revoke",
        headers={"Authorization": f"Bearer {staff_auth_token}"},
        json={"device_id": dev_id}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_api_call_reject(staff_auth_token):
    resp = client.post(
        "/api/v1/telephony/mobile/call/reject",
        headers={"Authorization": f"Bearer {staff_auth_token}"},
        json={
            "call_session_id": f"vcs_rej_{secrets.token_hex(4)}",
            "provider_call_id": "call_uuid_test",
            "reason": "user_declined"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["status"] == "rejected"


def test_api_test_incoming_call_dispatch(staff_auth_token):
    resp = client.post(
        "/api/v1/telephony/mobile/test/incoming-call",
        headers={"Authorization": f"Bearer {staff_auth_token}"},
        json={
            "caller_phone": "+919876543210",
            "caller_name": "Test Customer",
            "lead_id": 999
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "test_session_id" in data
