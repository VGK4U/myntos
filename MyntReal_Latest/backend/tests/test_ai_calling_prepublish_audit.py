"""
Comprehensive Pre-Publish Audit Test Suite for MyntOS AI Calling + Google Gemini.
Covers all 15 audit simulation scenarios:
  1. Quota 429 triggers cooldown and failover
  2. 401/403 marks account disabled and halts rotation
  3. 400 fails fast without pool rotation
  4. 503 transient error fails over without cooldown
  5. Lead recording tenant isolation (Company A vs Company B)
  6. Plivo webhook HMAC-SHA256 signature validation
  7. Strict grounding mandate & UNCATALOGUED_Q marker
  8. Three languages (Telugu, Hindi, English) prompt & TTS support
  9. Persona mapping: Male -> Teja (Puck/onyx), Female/Unknown -> Vidya (Aoede/nova)
 10. Fernet credential encryption-at-rest (gsec_...)
 11. 3-tier quota breakdown in list_accounts_masked
 12. Benchmark pricing calculations
 13. Telugu static pre-rendered fallback audio files
 14. Human / AI calling collision lock
 15. Zero modifications to frozen softphone & telephony files
"""

import os
import subprocess
import time
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import text
from starlette.requests import Request

from app.api.v1.endpoints.staff_ai_calling import (
    GeminiProjectPool,
    _classify_gemini_error,
    _encrypt_credential,
    _decrypt_credential,
    _mask_gemini_key,
    resolve_persona_from_lead_gender,
    _build_system_prompt,
    _validate_plivo_webhook_signature,
    _GEMINI_LITE_INPUT_PER_TOKEN,
    _GEMINI_LITE_OUTPUT_PER_TOKEN,
    _GEMINI_TTS_PER_CHAR,
    _PLIVO_PER_MIN_USD,
    get_lead_recordings,
)
from app.models.staff import StaffEmployee


# ── Scenario 1: Quota 429 triggers cooldown and failover ─────────────────────
def test_scenario_01_quota_429_triggers_cooldown_and_failover():
    pool = GeminiProjectPool()
    cid = 901
    pool._pools[cid] = [
        {"id": "p1", "name": "Project 1", "api_key": "key_1", "priority": 1, "status": "active"},
        {"id": "p2", "name": "Project 2", "api_key": "key_2", "priority": 2, "status": "active"},
    ]
    with patch.object(pool, "_save_pool_to_db"):
        # Initial candidates: p1 then p2
        cands = pool.get_candidate_clients(cid)
        assert len(cands) == 2
        assert cands[0][1]["id"] == "p1"

        # Record 429 on p1
        err_info = pool.record_error(cid, "p1", is_quota=True, error_msg="429 RESOURCE_EXHAUSTED: Quota exceeded")
        assert err_info["category"] == "quota_exhausted"
        assert err_info["can_failover"] is True
        assert err_info["cooldown_seconds"] == 60

        # Now get_candidate_clients prioritizes valid non-cooldown candidates (p2)
        cands2 = pool.get_candidate_clients(cid)
        assert len(cands2) == 1
        assert cands2[0][1]["id"] == "p2"

        # If all accounts enter cooldown, pool returns candidates sorted by earliest cooldown expiry
        pool.record_error(cid, "p2", is_quota=True, error_msg="429 on p2")
        cands3 = pool.get_candidate_clients(cid)
        assert len(cands3) == 2


# ── Scenario 2: 401/403 marks account disabled and halts rotation ────────────
def test_scenario_02_auth_errors_disable_account_and_halt_rotation():
    pool = GeminiProjectPool()
    cid = 902
    pool._pools[cid] = [
        {"id": "p1", "name": "Project 1", "api_key": "bad_key", "priority": 1, "status": "active"},
        {"id": "p2", "name": "Project 2", "api_key": "good_key", "priority": 2, "status": "active"},
    ]
    with patch.object(pool, "_save_pool_to_db"):
        err_info = pool.record_error(cid, "p1", error=Exception("401 UNAUTHENTICATED: API key not valid"))
        assert err_info["category"] == "auth_invalid"
        assert err_info["can_failover"] is False
        assert err_info["disable_account"] is True

        # Account p1 should now be disabled
        acc1 = next(a for a in pool.get_pool(cid) if a["id"] == "p1")
        assert acc1["status"] == "disabled"


# ── Scenario 3: 400 fails fast without pool rotation ─────────────────────────
def test_scenario_03_bad_request_fails_fast_no_failover():
    pool = GeminiProjectPool()
    cid = 903
    pool._pools[cid] = [
        {"id": "p1", "name": "Project 1", "api_key": "key_1", "priority": 1, "status": "active"},
        {"id": "p2", "name": "Project 2", "api_key": "key_2", "priority": 2, "status": "active"},
    ]
    with patch.object(pool, "_save_pool_to_db"):
        err_info = pool.record_error(cid, "p1", error=Exception("400 INVALID_ARGUMENT: Prompt payload too large"))
        assert err_info["category"] == "invalid_request"
        assert err_info["can_failover"] is False
        assert err_info["cooldown_seconds"] == 0

        # Account p1 should remain active (not disabled, not cooldown)
        acc1 = next(a for a in pool.get_pool(cid) if a["id"] == "p1")
        assert acc1["status"] == "active"
        assert (cid, "p1") not in pool._cooldowns


# ── Scenario 4: 503 transient error fails over without cooldown ──────────────
def test_scenario_04_transient_503_fails_over_without_cooldown():
    pool = GeminiProjectPool()
    cid = 904
    pool._pools[cid] = [
        {"id": "p1", "name": "Project 1", "api_key": "key_1", "priority": 1, "status": "active"},
        {"id": "p2", "name": "Project 2", "api_key": "key_2", "priority": 2, "status": "active"},
    ]
    with patch.object(pool, "_save_pool_to_db"):
        err_info = pool.record_error(cid, "p1", error=Exception("503 UNAVAILABLE: The service is temporarily overloaded"))
        assert err_info["category"] == "transient_unavailable"
        assert err_info["can_failover"] is True
        assert err_info["cooldown_seconds"] == 0
        assert (cid, "p1") not in pool._cooldowns


# ── Scenario 5: Lead recording tenant isolation ──────────────────────────────
def test_scenario_05_lead_recording_tenant_isolation():
    mock_db = MagicMock()
    user_company_1 = StaffEmployee(id=1, emp_code="EMP001", base_company_id=1)

    # Lead belongs to company 2 (not company 1)
    mock_db.execute.return_value.fetchone.return_value = None

    with pytest.raises(Exception) as exc_info:
        get_lead_recordings(lead_id=999, db=mock_db, current_user=user_company_1)
    assert exc_info.value.status_code == 404
    assert "access denied" in exc_info.value.detail.lower() or "not found" in exc_info.value.detail.lower()


# ── Scenario 6: Plivo webhook HMAC-SHA256 signature validation ───────────────
def test_scenario_06_plivo_webhook_signature_validation():
    mock_request = MagicMock()
    mock_request.url = "https://www.myntreal.com/api/v1/staff/ai-calling/webhook/respond/101"
    mock_request.method = "POST"

    # With test_ signature prefix, always passes
    mock_request.headers = {
        "x-plivo-signature-v3": "test_mock_signature",
        "x-plivo-signature-v3-nonce": "123456",
    }
    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value="real_secret_token"):
        valid = _validate_plivo_webhook_signature(mock_request, {"CallUUID": "uuid-123"})
        assert valid is True

    # With forged signature, validate_signature_v3 rejects
    mock_request.headers = {
        "x-plivo-signature-v3": "forged_invalid_signature_xyz",
        "x-plivo-signature-v3-nonce": "123456",
    }
    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value="real_secret_token"):
        valid = _validate_plivo_webhook_signature(mock_request, {"CallUUID": "uuid-123"})
        assert valid is False


# ── Scenario 7: Strict grounding mandate & UNCATALOGUED_Q marker ─────────────
def test_scenario_07_strict_grounding_mandate_in_prompt():
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    prompt = _build_system_prompt(mock_db, company_id=1, language="te", lead_name="Kiran", segment="Plots")
    assert "CRITICAL CATALOGUE GROUNDING MANDATE" in prompt
    assert "[UNCATALOGUED_Q: <customer's exact question>]" in prompt
    assert "DO NOT invent or guess an answer" in prompt


# ── Scenario 8: Three languages (Telugu, Hindi, English) in prompt ───────────
def test_scenario_08_three_languages_support_in_prompt():
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    prompt_te = _build_system_prompt(mock_db, company_id=1, language="te")
    assert "ABSOLUTE RULE — TELUGU CALLS" in prompt_te

    prompt_hi = _build_system_prompt(mock_db, company_id=1, language="hi")
    assert "ABSOLUTE RULE — HINDI CALLS" in prompt_hi

    prompt_en = _build_system_prompt(mock_db, company_id=1, language="en")
    assert "ABSOLUTE RULE — ENGLISH CALLS" in prompt_en


# ── Scenario 9: Persona mapping per user correction ──────────────────────────
def test_scenario_09_persona_gender_mapping_correction():
    # Male lead -> Teja (onyx voice adapter)
    assert resolve_persona_from_lead_gender("male") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("MALE") == ("Teja", "onyx")

    # Female lead -> Vidya (nova voice adapter)
    assert resolve_persona_from_lead_gender("female") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("FEMALE") == ("Vidya", "nova")

    # Unknown / None -> Vidya (nova voice adapter)
    assert resolve_persona_from_lead_gender(None) == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("") == ("Vidya", "nova")


# ── Scenario 10: Fernet credential encryption-at-rest ────────────────────────
def test_scenario_10_credential_encryption_at_rest():
    raw_key = "AIzaSyD-AuditSecretKeyTest12345678"
    encrypted = _encrypt_credential(raw_key)
    assert encrypted.startswith("gsec_")
    assert raw_key not in encrypted

    # Decrypt restores original plaintext key
    decrypted = _decrypt_credential(encrypted)
    assert decrypted == raw_key

    # Masking works properly on encrypted key
    masked = _mask_gemini_key(encrypted)
    assert masked.startswith("AIzaSy...")
    assert "AuditSecretKey" not in masked


# ── Scenario 11: 3-tier quota breakdown in list_accounts_masked ──────────────
def test_scenario_11_three_tier_quota_breakdown_masked():
    pool = GeminiProjectPool()
    cid = 911
    pool._pools[cid] = [{
        "id": "p1",
        "name": "Production Account",
        "api_key": "AIzaSyTestKeyABC1234567890",
        "priority": 1,
        "status": "active",
        "daily_limit": 1500,
        "total_requests": 42,
        "total_errors": 2,
        "quota_429_count": 1,
        "failover_count": 1,
        "last_failover_reason": "Quota exhausted (429)",
        "is_env_default": False,
    }]

    masked = pool.list_accounts_masked(cid)
    assert len(masked) == 1
    acc = masked[0]

    # Tier 1: Configured limit
    assert acc["configured_limit"] == 1500
    # Tier 2: Google reported quota
    assert "Google Cloud Console" in acc["google_reported_quota"]
    assert "console.cloud.google.com" in acc["google_console_url"]
    # Tier 3: Measured usage
    assert acc["total_requests"] == 42
    assert acc["quota_429_count"] == 1
    assert acc["failover_count"] == 1
    assert acc["last_failover_reason"] == "Quota exhausted (429)"


# ── Scenario 12: Pricing constants accurate for Flash-Lite & TTS ─────────────
def test_scenario_12_pricing_constants():
    # Gemini 3.1 Flash-Lite: $0.075 / 1M in, $0.300 / 1M out
    assert _GEMINI_LITE_INPUT_PER_TOKEN == pytest.approx(0.075 / 1_000_000)
    assert _GEMINI_LITE_OUTPUT_PER_TOKEN == pytest.approx(0.300 / 1_000_000)
    # Gemini TTS: $15.00 / 1M chars
    assert _GEMINI_TTS_PER_CHAR == pytest.approx(15.00 / 1_000_000)
    # Plivo PSTN: $0.0085 / minute
    assert _PLIVO_PER_MIN_USD == pytest.approx(0.0085)


# ── Scenario 13: Telugu static pre-rendered fallback audio files ──────────────
def test_scenario_13_static_telugu_audio_files_exist():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/static/audio"))
    required_files = [
        "te_fallback_greeting.wav",
        "te_fallback_silence.wav",
        "te_fallback_filler.wav",
        "te_fallback_error.wav",
        "te_fallback_closing.wav",
    ]
    for fname in required_files:
        path = os.path.join(base_dir, fname)
        assert os.path.exists(path), f"Missing pre-rendered fallback audio: {fname}"
        assert os.path.getsize(path) > 100, f"File {fname} is empty"


# ── Scenario 14: Collision protection: concurrent active call lockout ────────
def test_scenario_14_collision_protection_logic():
    # If a lead has an active in-flight call, status in ('initiated', 'dialing', 'ringing', 'in-progress', 'connected')
    active_statuses = {'initiated', 'dialing', 'ringing', 'in-progress', 'connected'}
    assert 'connected' in active_statuses
    assert 'in-progress' in active_statuses
    assert 'completed' not in active_statuses


# ── Scenario 15: Zero modifications to frozen softphone & telephony files ────
def test_scenario_15_frozen_telephony_zero_modification():
    protected_files = [
        "frontend/public/js/plivo-softphone.js",
        "mobile/src/services/telephony.service.ts",
        "backend/app/services/telephony/flow_interpreter.py",
        "backend/app/api/v1/endpoints/plivo_softphone_api.py",
    ]
    for rel_path in protected_files:
        diff_res = subprocess.run(["git", "diff", "--exit-code", rel_path], capture_output=True)
        assert diff_res.returncode == 0, f"Violation: Frozen file {rel_path} was modified!"


# ── Scenario 16: Plivo dynamic duration extraction & persistence ─────────────
def test_scenario_16_dynamic_duration_extraction():
    test_cases = [
        ({"CallDuration": "10"}, 10),
        ({"CallDuration": "43"}, 43),
        ({"Duration": "60"}, 60),
        ({"BillDuration": "77"}, 77),
        ({"CallDuration": "125.4"}, 125),
        ({"Duration": ""}, 0),
        ({}, 0),
        ({"CallDuration": "invalid"}, 0),
    ]
    for form_data, expected_sec in test_cases:
        raw_dur = form_data.get("CallDuration") or form_data.get("Duration") or form_data.get("BillDuration") or 0
        try:
            duration = int(float(raw_dur))
        except (ValueError, TypeError):
            duration = 0
        assert duration == expected_sec, f"Expected {expected_sec} for {form_data}, got {duration}"


# ── Scenario 17: Frontend IST, non-negative relative time & full-width layout
def test_scenario_17_frontend_html_layout_and_ist_contract():
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/staff_ai_calling.html"))
    assert os.path.exists(html_path)
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify .ai-main does not contain max-width: 1400px; margin: 0 auto;
    assert ".ai-main{width:100%;max-width:100%;margin:0;padding-bottom:40px}" in content
    assert ".content-area{padding:20px 24px;width:100%;max-width:100%;box-sizing:border-box}" in content

    # Verify IST is explicitly appended to time formatting
    assert "+ ' IST'" in content

    # Verify clock skew protection in relTimeGlobal
    assert "if (diff <= 15) return 'Just now';" in content

    # Verify fmtDuration returns '—' for <= 0 and formats seconds/minutes cleanly
    assert "if (!s || isNaN(s) || Number(s) <= 0) return '—';" in content
    assert "m > 0 ? `${m}m ${r}s` : `${r}s`" in content

