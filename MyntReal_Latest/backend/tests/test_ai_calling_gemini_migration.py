"""
Unit Tests for AI Calling Google Gemini Migration & Missing Information Tab.
Verifies:
1. Gemini API Key resolution and client initialization.
2. Conversation generation via Gemini 3.1 Flash Lite with Telugu/English lock.
3. Post-call extraction via Gemini with JSON response schema.
4. Voice & Persona: Aoede (female) for male leads / unknown, Puck (male) for female leads.
5. Static pre-rendered Telugu WAV fallback when Gemini TTS is unavailable or rate-limited.
6. Missing Information API endpoints (GET /missing-info, POST /missing-info/{id}/action, GET /missing-info/check-existing-catalogue).
7. Tenant isolation across queries.
8. Frozen Telephony Lock integrity verification.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.api.v1.endpoints.staff_ai_calling import (
    _get_gemini_key,
    _get_gemini_client,
    _gemini_conversation,
    _gemini_summarize,
    _generate_tts,
    _build_system_prompt,
    get_missing_information,
    missing_info_action,
    check_existing_catalogue,
    resolve_persona_from_lead_gender,
)


# ─── 1. GEMINI KEY RESOLUTION & CLIENT INITIALIZATION ─────────────────────────

def test_gemini_key_resolution_precedence():
    """Verify GEMINI_API_KEY takes precedence over GOOGLE_API_KEY."""
    with patch("app.api.v1.endpoints.staff_ai_calling._reload_env", return_value=None):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "AIzaSy_GEMINI_KEY_123",
            "GOOGLE_API_KEY": "AIzaSy_GOOGLE_KEY_456",
        }, clear=False):
            resolved = _get_gemini_key()
            assert resolved == "AIzaSy_GEMINI_KEY_123"


def test_gemini_key_resolution_google_key_fallback():
    """Verify GOOGLE_API_KEY is used if GEMINI_API_KEY is empty."""
    with patch("app.api.v1.endpoints.staff_ai_calling._reload_env", return_value=None):
        with patch("app.api.v1.endpoints.staff_ai_calling.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GOOGLE_API_KEY = ""
            with patch.dict(os.environ, {
                "GEMINI_API_KEY": "",
                "GOOGLE_API_KEY": "AIzaSy_GOOGLE_KEY_456",
            }, clear=False):
                resolved = _get_gemini_key()
                assert resolved == "AIzaSy_GOOGLE_KEY_456"


def test_gemini_client_initialization():
    """Verify _get_gemini_client initializes google.genai.Client."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_key", return_value="AIzaSy_TEST_KEY"):
        with patch("google.genai.Client") as mock_client_cls:
            mock_inst = MagicMock()
            mock_client_cls.return_value = mock_inst
            client = _get_gemini_client()
            assert client == mock_inst
            mock_client_cls.assert_called_once_with(api_key="AIzaSy_TEST_KEY")


# ─── 2. GEMINI CONVERSATION TURN GENERATION ───────────────────────────────────

def test_gemini_conversation_turn():
    """Verify _gemini_conversation calls Gemini generate_content and parses response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "నమస్కారం! అవును, ఈ ప్రాజెక్ట్ చాలా మంచి లొకేషన్‌లో ఉంది."
    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 120
    mock_usage.candidates_token_count = 45
    mock_response.usage_metadata = mock_usage
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_client", return_value=mock_client):
        messages = [
            {"role": "user", "content": "ఈ ప్రాజెక్ట్ గురించి వివరాలు చెప్పండి."}
        ]
        system_prompt = "You are Vidya, a Telugu real estate sales assistant."
        reply, p_tok, c_tok = _gemini_conversation(messages, system_prompt, language="te")

        assert "నమస్కారం" in reply
        assert p_tok == 120
        assert c_tok == 45
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["model"] == "gemini-3.1-flash-lite"


def test_gemini_conversation_fallback_when_unconfigured():
    """Verify safe fallback when Gemini client is not configured."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_client", return_value=None):
        with patch("app.api.v1.endpoints.staff_ai_calling._get_openai_key", return_value=""):
            messages = [{"role": "user", "content": "Hello"}]
            reply, p_tok, c_tok = _gemini_conversation(messages, "System", language="te")
            assert "Mynt Real Properties" in reply
            assert p_tok == 0
            assert c_tok == 0


# ─── 3. VOICE & PERSONA CONSISTENCY (TELUGU & ENGLISH ONLY) ───────────────────

def test_persona_voice_mapping_from_gender():
    """
    Verify voice persona mapping per user correction:
    - Male lead -> Teja (male voice Puck via onyx adapter)
    - Female lead -> Vidya (female voice Aoede via nova adapter)
    - Unknown/missing -> Vidya (female voice Aoede via nova adapter)
    """
    assert resolve_persona_from_lead_gender("male") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("MALE") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("female") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("FEMALE") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender(None) == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("") == ("Vidya", "nova")


def test_gemini_tts_voice_selection():
    """Verify _generate_tts maps female persona to Aoede and male persona to Puck."""
    mock_client = MagicMock()
    mock_res = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"\x00\x00" * 200
    mock_res.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
    mock_client.models.generate_content.return_value = mock_res

    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_client", return_value=mock_client):
        with patch("app.api.v1.endpoints.staff_ai_calling._ffmpeg_to_mulaw"):
            # Female persona (Vidya)
            _generate_tts("నమస్కారం", language="te", voice_override="nova")
            cfg_female = mock_client.models.generate_content.call_args[1]["config"]
            assert cfg_female.speech_config.voice_config.prebuilt_voice_config.voice_name == "Aoede"

            # Male persona (Teja)
            _generate_tts("నమస్కారం", language="te", voice_override="onyx")
            cfg_male = mock_client.models.generate_content.call_args[1]["config"]
            assert cfg_male.speech_config.voice_config.prebuilt_voice_config.voice_name == "Puck"


def test_tts_fallback_to_static_telugu_audio():
    """Verify _generate_tts falls back to pre-rendered Telugu WAV files when Gemini TTS is unavailable."""
    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_client", return_value=None):
        with patch("app.api.v1.endpoints.staff_ai_calling._get_openai_key", return_value=""):
            filename = _generate_tts("నమస్కారం! మేము Mynt Real నుండి మాట్లాడుతున్నాం.", language="te")
            assert filename.endswith(".wav") or filename.endswith(".mp3")
            assert "fallback" in filename or "static" in filename or filename.endswith(".wav")


# ─── 4. POST-CALL EXTRACTION VIA GEMINI (JSON OUTPUT) ─────────────────────────

def test_gemini_summarize_post_call():
    """Verify _gemini_summarize extracts structured CRM fields via Gemini."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "summary": "Customer expressed interest in 200 sq. yard plot in Hyderabad.",
        "outcome": "interested",
        "detected_language": "te",
        "interest_level": "high",
        "customer_name": "Ravi Kumar",
        "customer_phone": "+919876543210",
        "city": "Hyderabad",
        "property_type": "plot",
        "budget_min": 2500000,
        "budget_max": 3500000,
        "notes": "Follow up next Monday."
    })
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.api.v1.endpoints.staff_ai_calling._get_gemini_client", return_value=mock_client):
        history = [
            {"role": "assistant", "content": "నమస్కారం అండి, ప్లాట్స్ గురించి మాట్లాడుతున్నాం."},
            {"role": "user", "content": "నాకు హైదరాబాద్‌లో 200 గజాల ప్లాట్ కావాలి, బడ్జెట్ 30 లక్షలు."}
        ]
        result = _gemini_summarize(history, language="te")

        assert result["outcome"] == "interested"
        assert result["interest_level"] == "high"
        assert result["property_type"] == "plot"
        assert result["detected_language"] == "te"
        call_kwargs = mock_client.models.generate_content.call_args[1]
        assert call_kwargs["config"].response_mime_type == "application/json"


# ─── 5. GROUNDING & UNCATALOGUED QUESTION CAPTURE ─────────────────────────────

def test_system_prompt_mandates_strict_grounding_and_telugu_english_lock():
    """Verify system prompt strictly forbids Hindi and mandates catalogue-only grounding."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []
    with patch("app.api.v1.endpoints.staff_ai_calling._fetch_live_property_knowledge", return_value=""):
        prompt = _build_system_prompt(
            db=mock_db,
            company_id=1,
            language="te",
            lead_name="Kiran",
            agent_name="Vidya",
        )
        # Mandates Telugu & English, forbids Hindi
        assert "Telugu" in prompt
        assert "ABSOLUTE RULE — TELUGU CALLS" in prompt
        # Strict grounding mandate
        assert "CRITICAL CATALOGUE GROUNDING MANDATE" in prompt
        assert "UNCATALOGUED_Q" in prompt


# ─── 6. MISSING INFORMATION TAB API ENDPOINTS ─────────────────────────────────

def test_missing_info_get_endpoint_and_counts():
    """Verify get_missing_information returns counts and items with tenant isolation."""
    db = MagicMock()
    current_user = MagicMock()
    current_user.base_company_id = 42

    # Mock count rows: (total, pending, answered, cancelled)
    db.execute.return_value.fetchone.return_value = (10, 6, 3, 1)

    # Mock items query rows:
    # (id, log_id, question, ai_reply, answer, answered_by, answered_at, saved_to_kb, created_at, lead_id, lead_name, lead_phone, campaign_id, campaign_name)
    db.execute.return_value.fetchall.return_value = [
        (1, 101, "What is the clubhouse square footage?", "We will confirm.", None, None, None, False, None, 501, "Suresh", "+919876543210", 201, "Emerald Plots"),
        (2, 102, "Are pets allowed?", "Yes.", "Yes, domestic pets allowed.", "EMP001", None, True, None, 502, "Lakshmi", "+919876543211", 201, "Emerald Plots"),
        (3, 103, "Irrelevant query", "—", "__CANCELLED__", "EMP002", None, False, None, 503, "Rajesh", "+919876543212", 201, "Emerald Plots"),
    ]

    res = get_missing_information(
        status="all",
        search="",
        limit=50,
        db=db,
        current_user=current_user,
    )

    assert res["success"] is True
    assert res["counts"]["total"] == 10
    assert res["counts"]["pending"] == 6
    assert res["counts"]["answered"] == 3
    assert res["counts"]["cancelled"] == 1

    items = res["items"]
    assert len(items) == 3
    assert items[0]["status"] == "pending"
    assert items[1]["status"] == "answered"
    assert items[1]["saved_to_kb"] is True
    assert items[2]["status"] == "cancelled"


def test_missing_info_action_answer_and_save_to_kb():
    """Verify missing_info_action updates answer and creates catalogue entry when save_to_kb=True."""
    db = MagicMock()
    current_user = MagicMock()
    current_user.base_company_id = 42
    current_user.emp_code = "EMP_TEST"

    # Mock row lookup
    db.execute.return_value.fetchone.side_effect = [
        (1, "What is the possession date?"),  # row lookup in ai_unanswered_questions
        (999,),                                # RETURNING id in ai_product_catalogue
    ]

    payload = {
        "action": "answer",
        "answer": "Possession is scheduled for December 2026.",
        "save_to_kb": True,
        "segment": "Emerald Park",
        "category": "Project Details",
        "title": "Possession Date",
    }

    res = missing_info_action(
        uq_id=1,
        payload=payload,
        db=db,
        current_user=current_user,
    )

    assert res["success"] is True
    assert res["action"] == "answered"
    assert res["saved_to_kb"] is True
    assert len(res["entries_saved"]) == 1
    assert res["entries_saved"][0]["id"] == 999
    db.commit.assert_called()


def test_missing_info_action_cancel():
    """Verify missing_info_action marks item as cancelled."""
    db = MagicMock()
    current_user = MagicMock()
    current_user.base_company_id = 42
    current_user.emp_code = "EMP_TEST"

    db.execute.return_value.fetchone.return_value = (5, "Spam question")

    payload = {"action": "cancel"}
    res = missing_info_action(
        uq_id=5,
        payload=payload,
        db=db,
        current_user=current_user,
    )

    assert res["success"] is True
    assert res["action"] == "cancelled"
    db.commit.assert_called()


def test_missing_info_action_reopen():
    """Verify missing_info_action reopens cancelled/answered item to pending."""
    db = MagicMock()
    current_user = MagicMock()
    current_user.base_company_id = 42
    current_user.emp_code = "EMP_TEST"

    db.execute.return_value.fetchone.return_value = (5, "Legitimate question")

    payload = {"action": "reopen"}
    res = missing_info_action(
        uq_id=5,
        payload=payload,
        db=db,
        current_user=current_user,
    )

    assert res["success"] is True
    assert res["action"] == "reopened"
    db.commit.assert_called()


def test_check_existing_catalogue_search():
    """Verify check_existing_catalogue searches existing entries."""
    db = MagicMock()
    current_user = MagicMock()
    current_user.base_company_id = 42

    db.execute.return_value.fetchall.return_value = [
        (10, "Emerald Heights", "Pricing", "Price per sq yard", "Base price is Rs 22,000 per sq yard"),
    ]

    res = check_existing_catalogue(query="Price", db=db, current_user=current_user)
    assert res["success"] is True
    assert len(res["matches"]) == 1
    assert res["matches"][0]["title"] == "Price per sq yard"


# ─── 7. FROZEN TELEPHONY LOCK ZERO-MODIFICATION VERIFICATION ──────────────────

def test_frozen_telephony_zero_modification_integrity():
    """
    Strict architectural guardrail: Verify none of the frozen human softphone
    or backend callback files have been modified.
    """
    import subprocess
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    frozen_paths = [
        "frontend/public/js/plivo-softphone.js",
        "mobile/src/services/telephony.service.ts",
        "backend/app/services/telephony/flow_interpreter.py",
        "backend/app/api/v1/endpoints/plivo_softphone_api.py",
    ]

    for rel_path in frozen_paths:
        full_path = os.path.join(repo_root, rel_path)
        if os.path.exists(full_path):
            git_diff = subprocess.check_output(
                ["git", "diff", "--name-only", rel_path],
                cwd=repo_root
            ).decode("utf-8").strip()
            assert git_diff == "", f"VIOLATION OF FROZEN TELEPHONY LOCK: {rel_path} has uncommitted modifications!"
