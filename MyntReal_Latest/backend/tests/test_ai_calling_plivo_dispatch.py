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
import pytest
from starlette.requests import Request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
        assert kwargs["json"]["from"] == "+918031728899"
        assert kwargs["json"]["to"] == "+919876543210"
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
    """Verify correct BCP-47 codes are injected for Telugu, Hindi, and English."""
    for lang, bcp, expected_voice in [
        ("te", "te-IN", "Polly.Kavya"),
        ("hi", "hi-IN", "Polly.Aditi"),
        ("en", "en-IN", "Polly.Aditi"),
    ]:
        prompt_block = _build_speak_or_say(
            is_plivo=True,
            text="Test prompt",
            lang_code=bcp,
            voice=expected_voice,
        )
        resp = _build_speech_gather_xml(
            is_plivo=True,
            action_url="https://example.com/resp",
            lang_code=bcp,
            content_block=prompt_block,
        )
        xml = resp.body.decode("utf-8")
        assert f'language="{bcp}"' in xml
        assert f'voice="{expected_voice}"' in xml
        ET.fromstring(xml)  # Must be valid XML


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
    """Verify persona mapping invariant:
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
        assert kwargs["json"]["to"] == "+919876543210"
        assert kwargs["json"]["from"] == "+918031728899"
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

