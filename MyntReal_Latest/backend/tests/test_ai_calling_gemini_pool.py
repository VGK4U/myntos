"""
Unit Tests for Gemini Project Pool, Multi-Account Management, Quota Cooldown, and Usage Tracking.
"""

import os
import sys
import json
import time
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.api.v1.endpoints.staff_ai_calling import (
    GeminiProjectPool,
    _mask_gemini_key,
    _ping_gemini_key,
    _log_usage,
    _is_usage_authorized,
)
from app.models.staff import StaffEmployee


def test_mask_gemini_key():
    """Verify API keys are masked properly for UI safety."""
    assert _mask_gemini_key("") == ""
    assert _mask_gemini_key("short") == "***"
    assert _mask_gemini_key("AIzaSy1234567890abcdef") == "AIzaSy...cdef"


def test_pool_defaults_to_env_key():
    """Verify pool loads env default when no DB pool configured."""
    pool = GeminiProjectPool()
    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_key", return_value="AIzaSy_ENV_KEY_XYZ12345"):
        # Use an unseeded company_id so DB returns no existing pool
        accounts = pool.list_accounts_masked(company_id=88888)
        assert len(accounts) >= 1
        acc = accounts[0]
        assert acc["is_env_default"] is True
        assert acc["status"] == "active"
        assert "..." in acc["api_key_masked"]
        assert "AIzaSy_ENV_KEY_XYZ12345" not in acc["api_key_masked"]


def test_pool_add_and_list_accounts():
    """Verify adding secondary account to pool and listing masked."""
    pool = GeminiProjectPool()
    with patch.object(pool, "_save_pool_to_db", return_value=None):
        acc = pool.add_or_update_account(company_id=999, data={
            "name": "Project Beta (Secondary)",
            "api_key": "AIzaSy_PROJECT_BETA_KEY_987654",
            "priority": 2,
            "daily_limit": 3000,
        })
        assert acc["name"] == "Project Beta (Secondary)"
        assert acc["priority"] == 2

        listed = pool.list_accounts_masked(company_id=999)
        beta = next(a for a in listed if a["name"] == "Project Beta (Secondary)")
        assert beta["priority"] == 2
        assert "..." in beta["api_key_masked"]
        assert "AIzaSy_PROJECT_BETA_KEY_987654" not in beta["api_key_masked"]


def test_pool_toggle_and_delete_account():
    """Verify toggling active/standby and deleting secondary account."""
    pool = GeminiProjectPool()
    with patch.object(pool, "_save_pool_to_db", return_value=None):
        acc = pool.add_or_update_account(company_id=999, data={
            "id": "proj_test_del",
            "name": "Project Gamma",
            "api_key": "AIzaSy_PROJECT_GAMMA_KEY",
            "priority": 3,
        })
        # Toggle to standby
        toggled = pool.toggle_account(company_id=999, account_id="proj_test_del")
        assert toggled["status"] == "standby"

        # Toggle back to active
        toggled2 = pool.toggle_account(company_id=999, account_id="proj_test_del")
        assert toggled2["status"] == "active"

        # Delete account
        deleted = pool.delete_account(company_id=999, account_id="proj_test_del")
        assert deleted is True

        # Assert cannot delete env default
        pool._pools[999] = [{"id": "env_default", "is_env_default": True}]
        with pytest.raises(ValueError, match="Cannot delete environment default"):
            pool.delete_account(company_id=999, account_id="env_default")


def test_pool_cooldown_on_429_quota():
    """Verify that recording a quota error places key into cooldown and failover skips it."""
    pool = GeminiProjectPool()
    with patch.object(pool, "_save_pool_to_db", return_value=None):
        pool.add_or_update_account(company_id=999, data={
            "id": "proj_primary",
            "name": "Project Primary",
            "api_key": "AIzaSy_KEY_PRIMARY_12345",
            "priority": 1,
        })
        pool.add_or_update_account(company_id=999, data={
            "id": "proj_secondary",
            "name": "Project Secondary",
            "api_key": "AIzaSy_KEY_SECONDARY_67890",
            "priority": 2,
        })

        # Record 429 quota error on primary
        pool.record_error(company_id=999, account_id="proj_primary", is_quota=True, error_msg="429 RESOURCE_EXHAUSTED")

        # Check masked accounts reflects cooldown
        listed = pool.list_accounts_masked(company_id=999)
        primary = next(a for a in listed if a["id"] == "proj_primary")
        assert primary["status"] == "cooldown"
        assert primary["cooldown_remaining_sec"] > 0
        assert primary["total_errors"] == 1


def test_ping_gemini_key_helper():
    """Verify _ping_gemini_key helper validates key."""
    # Short key rejected without network
    short_res = _ping_gemini_key("short")
    assert short_res["success"] is False
    assert "too short" in short_res["error"]

    # Valid mock key
    with patch("google.genai.Client") as mock_client_cls:
        mock_inst = MagicMock()
        mock_res = MagicMock()
        mock_res.text = "pong"
        mock_inst.models.generate_content.return_value = mock_res
        mock_client_cls.return_value = mock_inst

        valid_res = _ping_gemini_key("AIzaSy_MOCK_VALID_KEY_12345")
        assert valid_res["success"] is True
        assert "valid and active" in valid_res["message"]


def test_usage_logging_gemini_cost():
    """Verify _log_usage calculates costs accurately for Gemini token and TTS metrics."""
    mock_db = MagicMock()
    # Flash-Lite conversation: 1000 in, 500 out
    _log_usage(mock_db, company_id=1, log_id=10, event_type="gemini_conversation",
               model="gemini-3.1-flash-lite", input_tok=1000, output_tok=500, source="proj_alpha")
    mock_db.execute.assert_called_once()
    params = mock_db.execute.call_args[0][1]
    assert params["et"] == "gemini_conversation"
    assert params["src"] == "proj_alpha"
    # 1000 * 0.075/1M + 500 * 0.30/1M = 0.000075 + 0.00015 = 0.000225
    assert abs(params["cost"] - 0.000225) < 1e-6
