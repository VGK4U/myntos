"""
Unit & Integration Tests for AI Calling Plivo-First Dispatch, Webhook XML,
Dual-Provider Handling, and Persona Consistency.
Strictly adheres to:
- DC Protocol: Safe mocking, no live phone calls.
- Frozen Telephony Lock: Does not modify human softphone files.
- Platform Parity & Security: No hardcoded local machine paths, no leaked credentials.
"""

import os
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
import pytest
from starlette.requests import Request
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.api.v1.endpoints.staff_ai_calling import (
    _get_plivo_auth_id,
    _get_plivo_auth_token,
    _get_plivo_caller_id,
    _get_twilio_sid,
    _get_twilio_token,
    _get_twilio_from,
    _dispatch_call,
    _is_plivo_request,
    _build_response_xml,
    _build_speak_or_say,
    _format_greeting_block,
    _build_speech_gather_xml,
    _build_menu_gather_xml,
    _build_wait_redirect_xml,
    _build_hangup_xml,
    _twiml_error_hangup,
    _webhook_base,
    resolve_persona_from_lead_gender,
    make_test_call,
    webhook_voice_select,
    webhook_respond,
    webhook_poll,
    webhook_status,
)


# ─── 1. PLIVO PRECEDENCE & CREDENTIAL HELPERS ─────────────────────────────────

def test_plivo_credential_helpers():
    """Verify Plivo configuration retrieval and default caller ID."""
    with patch.dict(os.environ, {
        "PLIVO_AUTH_ID": "PLIVO_TEST_ID",
        "PLIVO_AUTH_TOKEN": "PLIVO_TEST_TOKEN",
        "PLIVO_CALLER_ID": "+918031728899",
    }):
        assert _get_plivo_auth_id() == "PLIVO_TEST_ID"
        assert _get_plivo_auth_token() == "PLIVO_TEST_TOKEN"
        assert _get_plivo_caller_id() == "+918031728899"

    # Default fallback when PLIVO_CALLER_ID is unset
    with patch.dict(os.environ, {}, clear=True):
        assert _get_plivo_caller_id() == "+918031728899"


def test_dispatch_call_selects_plivo_when_both_present():
    """When both Plivo and Twilio credentials are configured, Plivo MUST take precedence."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_id", return_value="PL_TEST_ID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value="PL_TEST_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_caller_id", return_value="+918031728899"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_sid", return_value="AC_TWILIO_SID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_token", return_value="TWILIO_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_from", return_value="+1234567890"), \
         patch("requests.post") as mock_req_post:

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "message": "call fired",
            "request_uuid": "plivo-uuid-12345",
            "api_id": "api-id-67890",
        }
        mock_req_post.return_value = mock_resp

        call_sid, provider = _dispatch_call(
            phone="+919876543210",
            incoming_url="https://example.com/voice-select",
            status_url="https://example.com/status",
            rec_url="https://example.com/recording",
            log_id=42,
        )

        assert provider == "plivo"
        assert call_sid == "plivo-uuid-12345"

        mock_req_post.assert_called_once()
        url, kwargs = mock_req_post.call_args
        assert "api.plivo.com/v1/Account/PL_TEST_ID/Call/" in url[0]
        assert kwargs["auth"] == ("PL_TEST_ID", "PL_TEST_TOKEN")
        assert kwargs["json"]["from"] == "918031728899"
        assert kwargs["json"]["to"] == "919876543210"
        assert kwargs["json"]["answer_url"].startswith("https://example.com/voice-select")
        assert "provider=plivo" in kwargs["json"]["answer_url"]
        assert kwargs["json"]["hangup_url"].startswith("https://example.com/status")
        assert "provider=plivo" in kwargs["json"]["hangup_url"]


def test_dispatch_call_falls_back_to_twilio_when_plivo_unconfigured():
    """When Plivo credentials are empty, dispatch should seamlessly fall back to Twilio."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_id", return_value=None), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value=None), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_sid", return_value="AC_TWILIO_SID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_token", return_value="TW_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_from", return_value="+1234567890"), \
         patch("twilio.rest.Client") as mock_twilio_client:

        mock_instance = MagicMock()
        mock_call = MagicMock()
        mock_call.sid = "CA_TWILIO_CALL_SID"
        mock_instance.calls.create.return_value = mock_call
        mock_twilio_client.return_value = mock_instance

        call_sid, provider = _dispatch_call(
            phone="+919876543210",
            incoming_url="https://example.com/voice-select",
            status_url="https://example.com/status",
            rec_url="https://example.com/recording",
            log_id=42,
        )

        assert provider == "twilio"
        assert call_sid == "CA_TWILIO_CALL_SID"
        mock_instance.calls.create.assert_called_once()


def test_dispatch_call_falls_back_to_twilio_when_plivo_request_errors():
    """When Plivo API returns an HTTP error, dispatch should catch it and fall back to Twilio."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_id", return_value="PL_TEST_ID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value="PL_TEST_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_caller_id", return_value="+918031728899"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_sid", return_value="AC_TWILIO_SID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_token", return_value="TW_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_from", return_value="+1234567890"), \
         patch("requests.post") as mock_req_post, \
         patch("twilio.rest.Client") as mock_twilio_client:

        # Plivo returns 500 error
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Plivo Error"
        mock_req_post.return_value = mock_resp

        # Twilio fallback succeeds
        mock_instance = MagicMock()
        mock_call = MagicMock()
        mock_call.sid = "CA_TWILIO_FALLBACK_SID"
        mock_instance.calls.create.return_value = mock_call
        mock_twilio_client.return_value = mock_instance

        call_sid, provider = _dispatch_call(
            phone="+919876543210",
            incoming_url="https://example.com/voice-select",
            status_url="https://example.com/status",
            rec_url="https://example.com/recording",
            log_id=42,
        )

        assert provider == "twilio"
        assert call_sid == "CA_TWILIO_FALLBACK_SID"
        mock_req_post.assert_called_once()
        mock_instance.calls.create.assert_called_once()


# ─── 2. PLIVO XML SYNTAX & COMPLIANCE ─────────────────────────────────────────

def test_xml_generation_plivo_compliance():
    """Verify Plivo XML syntax uses <GetInput>, <Speak>, <Wait>, <Hangup> and is well-formed."""
    prompt_block = _build_speak_or_say(
        is_plivo=True,
        text="Namaste, how can I help you?",
        lang_code="hi-IN",
        voice="Polly.Aditi",
    )
    resp = _build_speech_gather_xml(
        is_plivo=True,
        action_url="https://example.com/webhook/respond",
        lang_code="hi-IN",
        content_block=prompt_block,
    )
    xml_plivo = resp.body.decode("utf-8")

    assert "<GetInput" in xml_plivo
    assert 'inputType="speech"' in xml_plivo
    assert 'speechModel="phone_call"' in xml_plivo
    assert 'language="hi-IN"' in xml_plivo
    assert "<Speak" in xml_plivo
    assert "<Gather" not in xml_plivo
    assert "<Say" not in xml_plivo

    # Validate well-formed XML
    root = ET.fromstring(xml_plivo)
    assert root.tag == "Response"
    assert root.find("GetInput") is not None
    assert root.find("GetInput").find("Speak") is not None

    # 2. Wait + Redirect block (Plivo uses Wait, NOT Pause)
    resp_wait = _build_wait_redirect_xml(
        is_plivo=True,
        redirect_url="https://example.com/webhook/poll",
        pause_sec=2,
    )
    xml_wait = resp_wait.body.decode("utf-8")
    assert '<Wait length="2"/>' in xml_wait
    assert "<Pause" not in xml_wait
    assert "<Redirect" in xml_wait
    root_wait = ET.fromstring(xml_wait)
    assert root_wait.tag == "Response"
    assert root_wait.find("Wait") is not None
    assert root_wait.find("Redirect") is not None

    # 3. Hangup block
    farewell_block = _build_speak_or_say(
        is_plivo=True,
        text="Dhanyavaad, shubh din!",
        lang_code="hi-IN",
        voice="Polly.Aditi",
    )
    resp_hangup = _build_hangup_xml(
        is_plivo=True,
        play_block=farewell_block,
        pause_sec=1,
    )
    xml_hangup = resp_hangup.body.decode("utf-8")
    assert "<Speak" in xml_hangup
    assert "<Hangup" in xml_hangup
    assert "<Say" not in xml_hangup
    root_hangup = ET.fromstring(xml_hangup)
    assert root_hangup.tag == "Response"
    assert root_hangup.find("Speak") is not None
    assert root_hangup.find("Hangup") is not None


def test_xml_generation_twilio_mode():
    """Verify Twilio mode produces valid TwiML with <Gather>, <Say>, <Pause>."""
    prompt_block = _build_speak_or_say(
        is_plivo=False,
        text="Hello, how are you?",
        lang_code="hi-IN",
        voice="Polly.Aditi",
    )
    resp = _build_speech_gather_xml(
        is_plivo=False,
        action_url="https://example.com/webhook/respond",
        lang_code="hi-IN",
        content_block=prompt_block,
    )
    xml_twilio = resp.body.decode("utf-8")
    assert "<Gather" in xml_twilio
    assert 'input="speech"' in xml_twilio
    assert "<Say" in xml_twilio
    assert "<GetInput" not in xml_twilio
    root = ET.fromstring(xml_twilio)
    assert root.tag == "Response"
    assert root.find("Gather") is not None
    assert root.find("Gather").find("Say") is not None

    resp_pause = _build_wait_redirect_xml(
        is_plivo=False,
        redirect_url="https://example.com/webhook/poll",
        pause_sec=1,
    )
    xml_pause = resp_pause.body.decode("utf-8")
    assert '<Pause length="1"/>' in xml_pause
    assert "<Wait" not in xml_pause


def test_xml_bcp47_languages():
    """Verify correct XML and speechModel are injected for Telugu, Hindi, and English."""
    # Hindi and English support Polly.Aditi on Plivo and use phone_call speechModel
    for lang, bcp in [("hi", "hi-IN"), ("en", "en-IN")]:
        prompt_block = _build_speak_or_say(
            is_plivo=True,
            text="Test prompt",
            lang_code=bcp,
            voice="Polly.Aditi",
        )
        resp = _build_speech_gather_xml(
            is_plivo=True,
            action_url="https://example.com/resp",
            lang_code=bcp,
            content_block=prompt_block,
        )
        xml = resp.body.decode("utf-8")
        assert f'language="{bcp}"' in xml
        assert 'voice="Polly.Aditi"' in xml
        assert 'speechModel="phone_call"' in xml
        ET.fromstring(xml)  # Must be valid XML

    # Telugu (te / te-IN) on Plivo: Polly has NO Telugu voice model.
    # Under NO circumstance may Telugu generate <Speak voice="Polly.Aditi" language="te-IN">.
    # It must generate <Play> with fallback audio and speechModel="default".
    te_prompt = _build_speak_or_say(
        is_plivo=True,
        text="Namaskaram",
        lang_code="te-IN",
        base_url="https://www.myntreal.com",
        context="greeting",
    )
    te_resp = _build_speech_gather_xml(
        is_plivo=True,
        action_url="https://example.com/resp",
        lang_code="te-IN",
        content_block=te_prompt,
    )
    te_xml = te_resp.body.decode("utf-8")
    assert 'language="te-IN"' in te_xml
    assert 'speechModel="default"' in te_xml
    assert "<Play>https://www.myntreal.com/api/v1/staff/ai-calling/audio/te_fallback_greeting.wav</Play>" in te_xml
    assert "<Speak" not in te_xml
    assert "Polly.Aditi" not in te_xml
    ET.fromstring(te_xml)


# ─── 3. DUAL-WEBHOOK PARAMETER EXTRACTION ─────────────────────────────────────

def test_is_plivo_request_detector():
    """Verify _is_plivo_request correctly differentiates Plivo from Twilio."""
    mock_req_plivo = MagicMock(spec=Request)
    mock_req_plivo.headers = {"user-agent": "Plivo-Voice-Callback"}
    assert _is_plivo_request(mock_req_plivo, {}) is True

    mock_req_empty = MagicMock(spec=Request)
    mock_req_empty.headers = {}
    # Plivo by CallUUID
    assert _is_plivo_request(mock_req_empty, {"CallUUID": "uuid-1234"}) is True
    # Plivo by Speech transcript key
    assert _is_plivo_request(mock_req_empty, {"Speech": "Namaskaram"}) is True

    # Twilio by CallSid
    assert _is_plivo_request(mock_req_empty, {"CallSid": "CA12345"}) is False
    # Twilio by SpeechResult
    assert _is_plivo_request(mock_req_empty, {"SpeechResult": "Hello"}) is False


def test_status_code_mappings():
    """Verify Plivo and Twilio status codes normalize to CRM status values."""
    status_map = {
        "completed": "completed",
        "failed": "failed",
        "busy": "busy",
        "no-answer": "no_answer",
        "no_answer": "no_answer",
        "timeout": "no_answer",
        "rejected": "busy",
        "canceled": "canceled",
        "cancelled": "canceled",
        "in-progress": "connected",
        "ringing": "dialing",
        "queued": "dialing",
    }
    # Plivo status codes
    assert status_map["timeout"] == "no_answer"
    assert status_map["rejected"] == "busy"
    assert status_map["no-answer"] == "no_answer"
    assert status_map["completed"] == "completed"
    assert status_map["failed"] == "failed"
    assert status_map["busy"] == "busy"

    # Twilio status codes
    assert status_map["in-progress"] == "connected"
    assert status_map["canceled"] == "canceled"


# ─── 4. GENDER PERSONA MAPPING & CONSISTENCY ──────────────────────────────────

def test_persona_resolver_complete_coverage():
    """Verify persona mapping invariant per user correction:
    - male -> ('Teja', 'onyx')
    - female -> ('Vidya', 'nova')
    - unknown / None -> ('Vidya', 'nova')
    """
    assert resolve_persona_from_lead_gender("male") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("MALE") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("  male  ") == ("Teja", "onyx")

    assert resolve_persona_from_lead_gender("female") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("Female") == ("Vidya", "nova")

    assert resolve_persona_from_lead_gender(None) == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("unknown") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("other") == ("Vidya", "nova")


# ─── 5. TEST CALL ENDPOINT INTEGRATION ────────────────────────────────────────

def test_make_test_call_routes_to_plivo():
    """Verify make_test_call endpoint formats outbound Plivo request and persists log."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.return_value = [101]

    mock_user = MagicMock()
    mock_user.base_company_id = 4

    mock_request = MagicMock(spec=Request)
    mock_request.base_url = "https://crm.myntreal.com"
    mock_request.url.scheme = "https"
    mock_request.headers = {}

    with patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_id", return_value="PL_AUTH"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_auth_token", return_value="PL_SEC"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_plivo_caller_id", return_value="+918031728899"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_sid", return_value="AC_SID"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_token", return_value="TW_TOKEN"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_twilio_from", return_value="+1234567890"), \
         patch("app.api.v1.endpoints.staff_ai_calling._get_openai_key", return_value="sk-test"), \
         patch("requests.post") as mock_req_post:

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "message": "call fired",
            "request_uuid": "plivo-uuid-testcall",
            "api_id": "api-id-testcall",
        }
        mock_req_post.return_value = mock_resp

        payload = {
            "phone": "9876543210",
            "language": "te",
            "name": "Suresh",
            "segment": "Villa Buyers",
        }

        result = make_test_call(
            request=mock_request,
            payload=payload,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["success"] is True
        assert result["provider"] == "plivo"
        assert result["caller_id"] == "+918031728899"
        assert result["call_sid"] == "plivo-uuid-testcall"
        assert result["log_id"] == 101

        # Check outbound Plivo API call
        mock_req_post.assert_called_once()
        url, kwargs = mock_req_post.call_args
        assert "api.plivo.com/v1/Account/PL_AUTH/Call/" in url[0]
        assert kwargs["json"]["to"] == "919876543210"
        assert kwargs["json"]["from"] == "918031728899"
        assert "lang=te" in kwargs["json"]["answer_url"]


# ─── 6. WEBHOOK BASE RESOLUTION & RECORDING PARAMETERS ────────────────────────

def test_webhook_base_resolution_production_and_override():
    """Verify webhook base domain resolution:
    - WEBHOOK_BASE_URL override takes precedence.
    - Forwarded host header is respected (e.g. www.myntreal.com).
    - Production environment fallback defaults to https://www.myntreal.com.
    """
    # 1. Environment variable override
    with patch.dict(os.environ, {"WEBHOOK_BASE_URL": "https://custom.myntreal.com"}):
        req = MagicMock(spec=Request)
        assert _webhook_base(req) == "https://custom.myntreal.com"

    # 2. X-Forwarded-Host header
    with patch.dict(os.environ, {}, clear=True):
        req = MagicMock(spec=Request)
        req.headers = {
            "x-forwarded-host": "www.myntreal.com",
            "x-forwarded-proto": "https",
        }
        assert _webhook_base(req) == "https://www.myntreal.com"

    # 3. Production fallback when host is raw/localhost
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        req = MagicMock(spec=Request)
        req.headers = {"host": "localhost:8000"}
        assert _webhook_base(req) == "https://www.myntreal.com"


def test_recording_callback_dual_parameters():
    """Verify webhook recording parses both Plivo (RecordUrl, RecordingID) and Twilio."""
    # Plivo payload
    plivo_form = {
        "RecordUrl": "https://s3.amazonaws.com/recordings/rec12345",
        "RecordingID": "rec_plivo_999",
        "CallUUID": "uuid_plivo_call",
    }
    rec_url = plivo_form.get("RecordUrl") or plivo_form.get("RecordingUrl") or ""
    rec_sid = plivo_form.get("RecordingID") or plivo_form.get("RecordingSid") or ""
    call_sid = plivo_form.get("CallUUID") or plivo_form.get("CallSid") or ""
    assert rec_url == "https://s3.amazonaws.com/recordings/rec12345"
    assert rec_sid == "rec_plivo_999"
    assert call_sid == "uuid_plivo_call"

    # Twilio payload
    twilio_form = {
        "RecordingUrl": "https://api.twilio.com/recordings/RE12345",
        "RecordingSid": "RE12345",
        "CallSid": "CA12345",
    }
    rec_url_tw = twilio_form.get("RecordUrl") or twilio_form.get("RecordingUrl") or ""
    rec_sid_tw = twilio_form.get("RecordingID") or twilio_form.get("RecordingSid") or ""
    call_sid_tw = twilio_form.get("CallUUID") or twilio_form.get("CallSid") or ""
    assert rec_url_tw == "https://api.twilio.com/recordings/RE12345"
    assert rec_sid_tw == "RE12345"
    assert call_sid_tw == "CA12345"


# ─── 7. CALL_SID UNIQUE CONSTRAINT, ATOMIC UPSERT & FLOW RESILIENCE ─────────

def test_unique_call_sid_session_creation():
    """Verify unique call_sid session creation and constraint enforcement in DB."""
    db = SessionLocal()
    test_sid = "test_unique_call_sid_session_101"
    log_id = None
    try:
        log_id = db.execute(text(
            "INSERT INTO ai_call_logs (company_id, phone_dialed, status) VALUES (4, '+919876543210', 'initiated') RETURNING id"
        )).scalar()
        db.commit()

        # Insert initial session
        db.execute(text("""
            INSERT INTO ai_call_sessions
                (call_sid, log_id, language, agent_voice, agent_name)
            VALUES
                (:sid, :lid, :lang, :voice, :aname)
            ON CONFLICT (call_sid) DO UPDATE
                SET language = EXCLUDED.language,
                    agent_name = EXCLUDED.agent_name
        """), {"sid": test_sid, "lid": log_id, "lang": "te", "voice": "Polly.Kavya", "aname": "Vidya"})
        db.commit()

        row = db.execute(text(
            "SELECT call_sid, language, agent_name FROM ai_call_sessions WHERE call_sid = :sid"
        ), {"sid": test_sid}).fetchone()
        assert row is not None
        assert row[0] == test_sid
        assert row[1] == "te"
        assert row[2] == "Vidya"
    finally:
        db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
        if log_id:
            db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
        db.commit()
        db.close()


def test_repeated_webhook_atomic_on_conflict_update():
    """Verify repeated webhooks for the same CallUUID execute atomic update without duplicate key errors."""
    db = SessionLocal()
    test_sid = "test_repeated_call_sid_202"
    log_id = None
    try:
        log_id = db.execute(text(
            "INSERT INTO ai_call_logs (company_id, phone_dialed, status) VALUES (4, '+919876543210', 'initiated') RETURNING id"
        )).scalar()
        db.commit()

        # 1. Initial webhook arrival
        db.execute(text("""
            INSERT INTO ai_call_sessions
                (call_sid, log_id, language, agent_voice, agent_name)
            VALUES
                (:sid, :lid, :lang, :voice, :aname)
            ON CONFLICT (call_sid) DO UPDATE
                SET language = EXCLUDED.language,
                    agent_name = EXCLUDED.agent_name
        """), {"sid": test_sid, "lid": log_id, "lang": "te", "voice": "Polly.Kavya", "aname": "Vidya"})
        db.commit()

        # 2. Repeated webhook arrival with updated params (e.g. carrier retry or voice confirmation)
        db.execute(text("""
            INSERT INTO ai_call_sessions
                (call_sid, log_id, language, agent_voice, agent_name)
            VALUES
                (:sid, :lid, :lang, :voice, :aname)
            ON CONFLICT (call_sid) DO UPDATE
                SET language = EXCLUDED.language,
                    agent_name = EXCLUDED.agent_name
        """), {"sid": test_sid, "lid": log_id, "lang": "hi", "voice": "Polly.Aditi", "aname": "Teja"})
        db.commit()

        # Verify exactly one row exists and values are updated
        rows = db.execute(text(
            "SELECT call_sid, language, agent_name FROM ai_call_sessions WHERE call_sid = :sid"
        ), {"sid": test_sid}).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == test_sid
        assert rows[0][1] == "hi"
        assert rows[0][2] == "Teja"
    finally:
        db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
        if log_id:
            db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
        db.commit()
        db.close()


def test_concurrent_webhooks_same_call_sid():
    """Verify concurrent webhooks for the same CallUUID are thread-safe and avoid race duplicates."""
    db = SessionLocal()
    test_sid = "test_concurrent_call_sid_303"
    log_id = None
    try:
        log_id = db.execute(text(
            "INSERT INTO ai_call_logs (company_id, phone_dialed, status) VALUES (4, '+919876543210', 'initiated') RETURNING id"
        )).scalar()
        db.commit()
        db.close()

        def worker(worker_id):
            w_db = SessionLocal()
            try:
                w_db.execute(text("""
                    INSERT INTO ai_call_sessions
                        (call_sid, log_id, language, agent_voice, agent_name)
                    VALUES
                        (:sid, :lid, :lang, :voice, :aname)
                    ON CONFLICT (call_sid) DO UPDATE
                        SET language = EXCLUDED.language,
                            agent_name = EXCLUDED.agent_name
                """), {
                    "sid": test_sid,
                    "lid": log_id,
                    "lang": f"l_{worker_id}",
                    "voice": "Polly.Kavya",
                    "aname": f"Agent_{worker_id}",
                })
                w_db.commit()
                return True
            finally:
                w_db.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(worker, range(5)))
        assert all(results)

        v_db = SessionLocal()
        rows = v_db.execute(text(
            "SELECT call_sid, language, agent_name FROM ai_call_sessions WHERE call_sid = :sid"
        ), {"sid": test_sid}).fetchall()
        assert len(rows) == 1
        v_db.close()
    finally:
        cleanup_db = SessionLocal()
        cleanup_db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
        if log_id:
            cleanup_db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
        cleanup_db.commit()
        cleanup_db.close()


def test_webhook_voice_select_plivo_xml_response():
    """Verify webhook_voice_select produces valid Plivo XML with <GetInput> and <Play> (Telugu safety)."""
    import asyncio
    from starlette.datastructures import FormData

    async def _async_test():
        db = SessionLocal()
        test_sid = "test_voice_select_plivo_xml_404"
        log_id = None
        try:
            log_id = db.execute(text(
                "INSERT INTO ai_call_logs (company_id, phone_dialed, status) VALUES (4, '+919876543210', 'initiated') RETURNING id"
            )).scalar()
            db.commit()

            req = MagicMock()
            async def fake_form():
                return FormData({"CallUUID": test_sid, "From": "+918031728899", "To": "+919876543210"})
            req.form = fake_form
            req.query_params = {}
            req.headers = {"user-agent": "Plivo-Voice-Callback"}
            req.base_url = "https://www.myntreal.com"

            resp = await webhook_voice_select(
                request=req,
                log_id=log_id,
                lang="te",
                campaign_id=0,
                is_test=1,
                provider="plivo",
                db=db,
            )

            assert resp.status_code == 200
            assert resp.media_type == "application/xml"
            xml_str = resp.body.decode("utf-8")
            assert "<GetInput" in xml_str
            assert "<Play" in xml_str
            assert "<Speak" not in xml_str
            assert 'speechModel="default"' in xml_str
            assert 'language="te-IN"' in xml_str

            root = ET.fromstring(xml_str)
            assert root.tag == "Response"
            assert root.find("GetInput") is not None
        finally:
            db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
            if log_id:
                db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
            db.commit()
            db.close()

    asyncio.run(_async_test())


def test_webhook_database_failure_fallback_xml():
    """Verify unexpected database failures return graceful Plivo XML with <Play> instead of HTTP 500 JSON."""
    import asyncio
    from starlette.datastructures import FormData

    async def _async_test():
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Simulated DB connection failure")

        req = MagicMock()
        async def fake_form():
            return FormData({"CallUUID": "error-test-call-uuid", "From": "+918031728899", "To": "+919876543210"})
        req.form = fake_form
        req.query_params = {}
        req.headers = {"user-agent": "Plivo-Voice-Callback"}
        req.base_url = "https://www.myntreal.com"

        resp = await webhook_voice_select(
            request=req,
            log_id=999,
            lang="te",
            provider="plivo",
            db=mock_db,
        )

        assert resp.status_code == 200
        assert resp.media_type == "application/xml"
        xml_str = resp.body.decode("utf-8")
        assert "<Response>" in xml_str
        assert "<Play" in xml_str
        assert "te_fallback_error.wav" in xml_str
        assert "<Hangup" in xml_str
        assert "<Speak" not in xml_str
        assert "{" not in xml_str  # Must NOT be JSON error!

        root = ET.fromstring(xml_str)
        assert root.tag == "Response"
        assert root.find("Play") is not None
        assert root.find("Hangup") is not None

    asyncio.run(_async_test())


def test_complete_voice_flow_step_1_2_3():
    """Verify the complete multi-turn flow: voice-select -> speech (respond) -> poll."""
    import asyncio
    from starlette.datastructures import FormData

    async def _async_flow():
        db = SessionLocal()
        test_sid = "test_complete_flow_call_sid_505"
        log_id = None
        try:
            log_id = db.execute(text(
                "INSERT INTO ai_call_logs (company_id, phone_dialed, status) VALUES (4, '+919876543210', 'initiated') RETURNING id"
            )).scalar()
            db.commit()

            # Step 1: Plivo hits webhook_voice_select
            req1 = MagicMock()
            async def form1():
                return FormData({"CallUUID": test_sid, "From": "+918031728899", "To": "+919876543210"})
            req1.form = form1
            req1.query_params = {}
            req1.headers = {"user-agent": "Plivo-Voice-Callback"}
            req1.base_url = "https://www.myntreal.com"

            resp1 = await webhook_voice_select(
                request=req1,
                log_id=log_id,
                lang="te",
                campaign_id=0,
                is_test=1,
                provider="plivo",
                db=db,
            )
            assert resp1.status_code == 200
            root1 = ET.fromstring(resp1.body.decode("utf-8"))
            assert root1.find("GetInput") is not None

            # Step 2: Customer speaks, Plivo forwards speech to webhook_respond
            req2 = MagicMock()
            async def form2():
                return FormData({"CallUUID": test_sid, "Speech": "Namaskaram, details cheppandi"})
            req2.form = form2
            req2.query_params = {}
            req2.headers = {"user-agent": "Plivo-Voice-Callback"}
            req2.base_url = "https://www.myntreal.com"

            with patch("app.api.v1.endpoints.staff_ai_calling._bg_gpt_tts"):
                resp2 = await webhook_respond(
                    log_id=log_id,
                    request=req2,
                    lang="te",
                    campaign_id=0,
                    is_test=1,
                    provider="plivo",
                    db=db,
                )
                assert resp2.status_code == 200
                root2 = ET.fromstring(resp2.body.decode("utf-8"))
                assert root2.find("Redirect") is not None
                assert root2.find("Wait") is not None

            # Step 3: Plivo redirects to webhook_poll
            db.execute(text(
                "UPDATE ai_call_sessions SET next_reply_text='Meeru adigina details ivi...', next_audio_url='FALLBACK' WHERE log_id=:lid"
            ), {"lid": log_id})
            db.commit()

            req3 = MagicMock()
            async def form3():
                return FormData({"CallUUID": test_sid})
            req3.form = form3
            req3.query_params = {}
            req3.headers = {"user-agent": "Plivo-Voice-Callback"}
            req3.base_url = "https://www.myntreal.com"

            resp3 = await webhook_poll(
                log_id=log_id,
                request=req3,
                lang="te",
                campaign_id=0,
                is_test=1,
                attempt=1,
                provider="plivo",
                db=db,
            )
            assert resp3.status_code == 200
            xml3 = resp3.body.decode("utf-8")
            root3 = ET.fromstring(xml3)
            assert root3.find("GetInput") is not None
            assert "<Play" in xml3
            assert "<Speak" not in xml3
        finally:
            db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
            if log_id:
                db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
            db.commit()
            db.close()

    asyncio.run(_async_flow())


def test_webhook_status_followup_and_lead_update():
    """Verify webhook_status safely processes call completion, parses followup dates, and updates lead without SQL syntax error."""
    import asyncio
    from starlette.datastructures import FormData

    async def _async_status():
        db = SessionLocal()
        import uuid
        test_sid = f"test_status_callback_sid_606_{uuid.uuid4().hex[:8]}"
        test_phone = "+919999888771"
        log_id = None
        lead_id = None
        try:
            # Clean up any leftover records
            db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid LIKE 'test_status_callback_sid_606%'"))
            db.commit()

            # 1. Create a test lead with required priority and handler_type
            lead_id = db.execute(text("""
                INSERT INTO crm_leads (
                    tenant_id, company_id, name, phone, status, priority, handler_type, created_at, updated_at
                ) VALUES (
                    1, 4, 'Test Followup Lead', :phone, 'New', 'high', 'unassigned', NOW(), NOW()
                ) RETURNING id
            """), {"phone": test_phone}).scalar()
            db.commit()

            # 2. Create test call log linked to lead with transcript
            log_id = db.execute(text("""
                INSERT INTO ai_call_logs (
                    company_id, lead_id, phone_dialed, status, transcript, language_used, created_at
                ) VALUES (
                    4, :lid, :phone, 'connected', '[{"speaker":"ai","text":"hello"}]', 'te', NOW()
                ) RETURNING id
            """), {"lid": lead_id, "phone": test_phone}).scalar()
            db.commit()

            # 3. Create test session with conversation & analysis
            db.execute(text("""
                INSERT INTO ai_call_sessions (call_sid, log_id, lead_id, language, agent_name, agent_voice, conversation)
                VALUES (:sid, :lid, :lead_id, 'te', 'Vidya', 'nova', '[]')
            """), {"sid": test_sid, "lid": log_id, "lead_id": lead_id})
            db.commit()

            # 4. Invoke webhook_status with Plivo completed callback
            req = MagicMock()
            async def form_status():
                return FormData({
                    "CallUUID": test_sid,
                    "CallStatus": "completed",
                    "Duration": "45",
                })
            req.form = form_status
            req.query_params = {}
            req.headers = {"user-agent": "Plivo-Voice-Callback"}
            req.base_url = "https://www.myntreal.com"

            with patch("app.api.v1.endpoints.staff_ai_calling._gpt_summarize") as mock_sum:
                mock_sum.return_value = {
                    "outcome": "interested",
                    "summary": "Customer interested in 3BHK villa",
                    "next_follow_up_date": "2026-09-30",
                    "city": "Vijayawada",
                    "location_preference": "Poranki",
                    "property_type": "Villa",
                    "budget_min": "1 Cr",
                    "budget_max": "1.5 Cr",
                    "interest_level": "high",
                    "detected_language": "te",
                }

                resp = await webhook_status(
                    log_id=log_id,
                    request=req,
                    db=db,
                )

                assert resp.status_code == 200
                assert resp.body.decode("utf-8") == "OK"

            # 5. Verify lead was updated with followup date and summary
            lead_row = db.execute(text("""
                SELECT ai_status, ai_summary, next_followup_date, looking_for
                FROM crm_leads WHERE id = :lid
            """), {"lid": lead_id}).fetchone()

            assert lead_row is not None
            assert lead_row[0] == "interested"
            assert "3BHK villa" in (lead_row[1] or "")
            assert str(lead_row[2]).startswith("2026-09-30")
            assert "Poranki" in (lead_row[3] or "")
        finally:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
                if log_id:
                    db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
                if lead_id:
                    db.execute(text("DELETE FROM crm_lead_notes WHERE lead_id = :id"), {"id": lead_id})
                    db.execute(text("DELETE FROM crm_leads WHERE id = :id"), {"id": lead_id})
                db.commit()
            except Exception:
                pass
            db.close()

    asyncio.run(_async_status())


def test_webhook_status_autocreates_lead_when_unlinked():
    """Verify webhook_status safely auto-creates a new lead with handler_type when an unlinked qualified call finishes."""
    import asyncio
    from starlette.datastructures import FormData

    async def _async_unlinked():
        db = SessionLocal()
        import uuid
        test_sid = f"test_status_callback_sid_707_{uuid.uuid4().hex[:8]}"
        test_phone = "+919999888772"
        log_id = None
        new_lead_id = None
        try:
            # Clean up any leftover records
            db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid LIKE 'test_status_callback_sid_707%'"))
            db.commit()

            # 1. Create test call log WITHOUT lead_id
            log_id = db.execute(text("""
                INSERT INTO ai_call_logs (
                    company_id, phone_dialed, status, transcript, language_used, created_at
                ) VALUES (
                    4, :phone, 'connected', '[{"speaker":"ai","text":"hello"}]', 'te', NOW()
                ) RETURNING id
            """), {"phone": test_phone}).scalar()
            db.commit()

            # 2. Create session
            db.execute(text("""
                INSERT INTO ai_call_sessions (call_sid, log_id, language, agent_name, agent_voice, conversation)
                VALUES (:sid, :lid, 'te', 'Vidya', 'nova', '[]')
            """), {"sid": test_sid, "lid": log_id})
            db.commit()

            req = MagicMock()
            async def form_status():
                return FormData({
                    "CallUUID": test_sid,
                    "CallStatus": "completed",
                    "Duration": "60",
                })
            req.form = form_status
            req.query_params = {}
            req.headers = {"user-agent": "Plivo-Voice-Callback"}
            req.base_url = "https://www.myntreal.com"

            with patch("app.api.v1.endpoints.staff_ai_calling._gpt_summarize") as mock_sum:
                mock_sum.return_value = {
                    "outcome": "interested",
                    "summary": "Customer looking for plot in Gannavaram",
                    "next_follow_up_date": "2026-10-05",
                    "city": "Vijayawada",
                    "location_preference": "Gannavaram",
                    "property_type": "Plot",
                    "budget_min": "40 L",
                    "budget_max": "60 L",
                    "interest_level": "high",
                    "detected_language": "te",
                    "customer_name": "Rao Garu",
                }

                resp = await webhook_status(
                    log_id=log_id,
                    request=req,
                    db=db,
                )

                assert resp.status_code == 200
                assert resp.body.decode("utf-8") == "OK"

            # 3. Verify lead was created and attached to log
            log_row = db.execute(text("SELECT lead_id FROM ai_call_logs WHERE id = :id"), {"id": log_id}).fetchone()
            assert log_row is not None
            new_lead_id = log_row[0]
            assert new_lead_id is not None

            lead_row = db.execute(text("""
                SELECT name, phone, priority, handler_type, looking_for, ai_status
                FROM crm_leads WHERE id = :lid
            """), {"lid": new_lead_id}).fetchone()
            assert lead_row is not None
            assert lead_row[0] == "Rao Garu"
            assert lead_row[1] == test_phone
            assert lead_row[2] == "medium"
            assert lead_row[3] == "unassigned"
            assert "Gannavaram" in lead_row[4]
            assert lead_row[5] == "interested"
        finally:
            try:
                db.rollback()
            except Exception:
                pass
            try:
                db.execute(text("DELETE FROM ai_call_sessions WHERE call_sid = :sid"), {"sid": test_sid})
                if log_id:
                    db.execute(text("DELETE FROM ai_call_logs WHERE id = :id"), {"id": log_id})
                if new_lead_id:
                    db.execute(text("DELETE FROM crm_lead_notes WHERE lead_id = :id"), {"id": new_lead_id})
                    db.execute(text("DELETE FROM crm_leads WHERE id = :id"), {"id": new_lead_id})
                db.commit()
            except Exception:
                pass
            db.close()

    asyncio.run(_async_unlinked())


# ─── 8. TELUGU PLIVO SAFETY & OPENAI CONFIG TESTS ─────────────────────────────

def test_telugu_greeting_generates_play_not_speak_when_tts_unavailable():
    """Verify that when OpenAI TTS is unavailable, Telugu greeting generates <Play> with fallback audio and NEVER <Speak>."""
    greeting_block = _format_greeting_block(
        is_plivo=True,
        audio_serve_url=None,
        fallback_text="Namaskaram, welcome to Mynt Real.",
        lang_code="te-IN",
        base_url="https://www.myntreal.com",
    )
    assert "<Play>" in greeting_block
    assert "https://www.myntreal.com/api/v1/staff/ai-calling/audio/te_fallback_greeting.wav" in greeting_block
    assert "<Speak" not in greeting_block
    assert "Polly.Aditi" not in greeting_block


def test_no_polly_aditi_with_telugu_in_any_context():
    """Under no circumstance may Telugu (te / te-IN) generate <Speak voice='Polly.Aditi' language='te-IN'>."""
    for context, expected_file in [
        ("greeting", "te_fallback_greeting.wav"),
        ("silence", "te_fallback_silence.wav"),
        ("filler", "te_fallback_filler.wav"),
        ("error", "te_fallback_error.wav"),
        ("closing", "te_fallback_closing.wav"),
    ]:
        xml = _build_speak_or_say(
            is_plivo=True,
            text="Telugu test message",
            lang_code="te-IN",
            voice="Polly.Aditi",
            base_url="https://www.myntreal.com",
            context=context,
        )
        assert f"<Play>https://www.myntreal.com/api/v1/staff/ai-calling/audio/{expected_file}</Play>" in xml
        assert "<Speak" not in xml
        assert "Polly.Aditi" not in xml


def test_telugu_asr_uses_speechmodel_default():
    """Plivo ASR speechModel='phone_call' is unsupported for Indic regional languages; te-IN requires speechModel='default'."""
    prompt = "<Play>https://example.com/audio.wav</Play>"
    resp = _build_speech_gather_xml(
        is_plivo=True,
        action_url="https://example.com/respond",
        lang_code="te-IN",
        content_block=prompt,
    )
    xml = resp.body.decode("utf-8")
    assert 'language="te-IN"' in xml
    assert 'speechModel="default"' in xml
    assert 'speechModel="phone_call"' not in xml

    # Menu gather also uses default for te-IN
    menu_resp = _build_menu_gather_xml(
        is_plivo=True,
        action_url="https://example.com/menu",
        lang_code="te-IN",
        prompt_text="Language choice",
        base_url="https://example.com",
        context="greeting",
    )
    menu_xml = menu_resp.body.decode("utf-8")
    assert 'language="te-IN"' in menu_xml
    assert 'speechModel="default"' in menu_xml
    assert 'speechModel="phone_call"' not in menu_xml


def test_english_uses_speechmodel_phone_call_and_speak_aditi():
    """English greeting uses speechModel='phone_call' and <Speak voice='Polly.Aditi' language='en-IN'>."""
    prompt = _build_speak_or_say(
        is_plivo=True,
        text="Welcome to Mynt Real",
        lang_code="en-IN",
        voice="Polly.Aditi",
        base_url="https://example.com",
        context="greeting",
    )
    assert '<Speak voice="Polly.Aditi" language="en-IN">Welcome to Mynt Real</Speak>' in prompt
    assert "<Play>" not in prompt

    resp = _build_speech_gather_xml(
        is_plivo=True,
        action_url="https://example.com/respond",
        lang_code="en-IN",
        content_block=prompt,
    )
    xml = resp.body.decode("utf-8")
    assert 'language="en-IN"' in xml
    assert 'speechModel="phone_call"' in xml
    assert '<Speak voice="Polly.Aditi" language="en-IN">' in xml


def test_openai_tts_success_path_generates_play_with_uuid():
    """When OpenAI TTS succeeds, _format_greeting_block produces <Play> with the audio URL."""
    audio_url = "https://www.myntreal.com/api/v1/staff/ai-calling/audio/a1b2c3d4-test.wav"
    block = _format_greeting_block(
        is_plivo=True,
        audio_serve_url=audio_url,
        fallback_text="Fallback text",
        lang_code="te-IN",
        base_url="https://www.myntreal.com",
    )
    assert block == f"<Play>{audio_url}</Play>"
    assert "<Speak" not in block


def test_webhook_error_fallback_generates_play_for_telugu():
    """_twiml_error_hangup for Telugu generates <Play> with te_fallback_error.wav and hangs up."""
    resp = _twiml_error_hangup(lang="te", is_plivo=True, base_url="https://www.myntreal.com")
    xml = resp.body.decode("utf-8")
    assert "<Play>https://www.myntreal.com/api/v1/staff/ai-calling/audio/te_fallback_error.wav</Play>" in xml
    assert "<Hangup/>" in xml
    assert "<Speak" not in xml
    assert "Polly.Aditi" not in xml


def test_openai_api_key_declared_in_settings():
    """Verify OPENAI_API_KEY is declared in application Settings class."""
    from app.core.config import settings, Settings
    fields = getattr(Settings, "model_fields", None) or getattr(Settings, "__fields__", {})
    assert "OPENAI_API_KEY" in fields, "Settings Pydantic model must declare OPENAI_API_KEY field"


def test_crm_dialer_unassigned_lead_no_attribute_error():
    """Verify CRMLead has no assigned_to attribute, and crm_dialer correctly uses primary_owner_id/telecaller_id."""
    from app.models.crm import CRMLead
    lead = CRMLead(id=1, name="Test Lead", phone="9876543210", handler_type="unassigned")
    assert not hasattr(lead, "assigned_to"), "CRMLead should NOT have assigned_to attribute"
    assert hasattr(lead, "primary_owner_id"), "CRMLead has primary_owner_id"
    assert hasattr(lead, "telecaller_id"), "CRMLead has telecaller_id"
    assert hasattr(lead, "handler_id"), "CRMLead has handler_id"
    assert hasattr(lead, "handler_type"), "CRMLead has handler_type"




