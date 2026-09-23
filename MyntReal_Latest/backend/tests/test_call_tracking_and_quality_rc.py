"""
Release Candidate Tests for Call Tracking & Quality Review
Validates:
1. Management overview includes KRA & task/solar time in OTHERS column.
2. Slot breakdown includes KRA & task/solar time in OTHERS column and org_totals.
3. System Administrator (MR10001) is excluded from CRM dashboard staff lists.
4. Quality review open-or-create endpoint functions properly without schema errors.
"""

import os
import sys
import pytest
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.call_tracking import CallQualityReview, StaffCallLog
from app.api.v1.endpoints.call_tracking import get_call_management_overview, get_call_slot_breakdown
from app.api.v1.endpoints.call_quality import open_or_create_review


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def admin_user(db_session):
    user = db_session.query(StaffEmployee).filter(StaffEmployee.id == 1).first()
    assert user is not None, "Admin user (id=1) must exist for testing"
    return user


def test_management_overview_others_kra_task(db_session, admin_user):
    """Verify management overview returns KRA and Task/Solar time in 'others'."""
    res = asyncio.run(get_call_management_overview(
        quick_range="this_month",
        db=db_session,
        current_user=admin_user
    ))
    assert res["success"] is True
    assert "overview" in res
    assert "per_staff" in res
    assert "other_hours" in res["overview"]
    assert "other_duration_seconds" in res["overview"]

    # Verify System Administrator MR10001 is excluded
    for s in res["per_staff"]:
        assert s.get("emp_code") != "MR10001", "MR10001 must be excluded from per_staff"
        assert "other_hours" in s
        assert "other_duration_seconds" in s
        assert "other_kra_minutes" in s
        assert "other_task_minutes" in s
        assert "other_breakdown" in s


def test_slot_breakdown_others_kra_task(db_session, admin_user):
    """Verify slot breakdown returns KRA and Task/Solar time in 'others'."""
    res = asyncio.run(get_call_slot_breakdown(
        quick_range="this_month",
        db=db_session,
        current_user=admin_user
    ))
    assert res["success"] is True
    assert "per_staff" in res
    assert "org_totals" in res

    org_total = res["org_totals"]["total"]
    assert "other_hours" in org_total
    assert "other_duration_seconds" in org_total

    # Verify System Administrator MR10001 is excluded and staff has breakdown
    for s in res["per_staff"]:
        assert s.get("emp_code") != "MR10001", "MR10001 must be excluded from slot breakdown"
        assert "other_hours" in s
        assert "other_duration_seconds" in s
        assert "other_kra_minutes" in s
        assert "other_task_minutes" in s
        assert "other_breakdown" in s


def test_open_or_create_quality_review(db_session, admin_user):
    """Verify call quality review can be opened or created without 'notes' TypeError."""
    call = db_session.query(StaffCallLog).filter(StaffCallLog.duration_seconds > 0).first()
    if call:
        body = {
            "call_session_id": call.device_call_id or f"test_session_{call.id}",
            "call_log_id": call.id,
            "staff_id": call.staff_id,
            "phone": call.phone_number or "9999999999"
        }
        res = open_or_create_review(
            body=body,
            db=db_session,
            current_user=admin_user
        )
        assert res is not None
        assert res.get("id") is not None
        assert res.get("staff_id") == call.staff_id
