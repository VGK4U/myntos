"""
Isolated Unit & Integration Tests for Sarvam AI Telephony Adapter.

Tests the 7 mandatory scenarios specified in the system instructions:
Test 1: 8kHz μ-law → Saaras v3 realtime (Direct μ-law pass-through configuration)
Test 2: 8kHz μ-law → Saaras v3 realtime → Telugu transcript
Test 3: 8kHz μ-law → Saaras v3 realtime → Hindi transcript
Test 4: 8kHz μ-law → Saaras v3 realtime → English transcript
Test 5: Telugu + English code-mixed speech (Tenglish)
Test 6: Hindi + English code-mixed speech (Hinglish)
Test 7: Customer interruption while AI audio is playing (Barge-in / clearAudio)
Bonus: Dynamic Cross-Vertical Knowledge Retrieval (Solar → Property → EV → Finance)
"""

import pytest
import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sarvam_telephony_adapter import (
    SarvamRealtimeSTTClient,
    SarvamStreamingTTSClient,
    DynamicKnowledgeEngine,
    PlivoBargeInController,
    SARVAM_STT_WS_URL,
    SARVAM_TTS_WS_URL
)


@pytest.fixture
def dummy_mulaw_8k_chunk():
    """Generate a sample 8kHz G.711 mu-law audio chunk (160 bytes = 20ms of silence/tone)."""
    raw_bytes = bytes([0xFF] * 160)
    return base64.b64encode(raw_bytes).decode("ascii")


# ==============================================================================
# TEST 1: 8kHz μ-law → Saaras v3 realtime (Direct Pass-through Configuration)
# ==============================================================================
def test_1_mulaw_8k_saaras_v3_configuration():
    """Verify that Sarvam Realtime STT client configures native 8kHz μ-law with saaras:v3-realtime."""
    client = SarvamRealtimeSTTClient(
        api_key="test_api_key_123",
        language_code="auto",
        model="saaras:v3-realtime",
        encoding="mulaw",
        sample_rate=8000,
        stream_type="balanced",
        endpointing="vad",
        mode="transcribe"
    )

    ws_url = client.build_ws_url()

    assert ws_url.startswith(SARVAM_STT_WS_URL)
    assert "model=saaras%3Av3-realtime" in ws_url or "model=saaras:v3-realtime" in ws_url
    assert "encoding=mulaw" in ws_url
    assert "sample_rate=8000" in ws_url
    assert "language_code=auto" in ws_url
    assert "endpointing=vad" in ws_url


# ==============================================================================
# TEST 2: 8kHz μ-law → Saaras v3 realtime → Telugu transcript
# ==============================================================================
def test_2_telugu_transcript_pipeline(dummy_mulaw_8k_chunk):
    """Verify Telugu speech recognition event handling and final transcript generation."""
    async def _run():
        received_final = []
        received_lang = []

        def on_final(text, lang):
            received_final.append(text)
            received_lang.append(lang)

        client = SarvamRealtimeSTTClient(
            api_key="test_api_key_123",
            language_code="te-IN",
            model="saaras:v3-realtime",
            encoding="mulaw",
            sample_rate=8000,
            on_final_transcript=on_final
        )

        mock_ws = AsyncMock()
        # Simulate Sarvam server messages for Telugu
        mock_messages = [
            json.dumps({"event": "session.begin", "request_id": "req-te-100"}),
            json.dumps({"event": "vad.speech_start", "utterance_idx": 0}),
            json.dumps({"event": "transcript.partial", "utterance_idx": 0, "text": "నమస్కారం", "language": "te-IN"}),
            json.dumps({"event": "vad.speech_end", "utterance_idx": 0}),
            json.dumps({"event": "transcript.final", "utterance_idx": 0, "text": "నమస్కారం! నాకు సోలార్ ప్యానెల్స్ గురించి సమాచారం కావాలి.", "language": "te-IN"}),
        ]

        async def mock_iter():
            for m in mock_messages:
                yield m

        mock_ws.__aiter__.side_effect = mock_iter

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            await client.connect()
            # Direct pass-through of 8kHz mu-law audio
            await client.send_audio_chunk(dummy_mulaw_8k_chunk)
            await asyncio.sleep(0.05)
            await client.close()

        assert len(received_final) == 1
        assert "సోలార్ ప్యానెల్స్" in received_final[0]
        assert received_lang[0] == "te-IN"

    asyncio.run(_run())


# ==============================================================================
# TEST 3: 8kHz μ-law → Saaras v3 realtime → Hindi transcript
# ==============================================================================
def test_3_hindi_transcript_pipeline(dummy_mulaw_8k_chunk):
    """Verify Hindi speech recognition event handling and final transcript generation."""
    async def _run():
        received_final = []
        received_lang = []

        def on_final(text, lang):
            received_final.append(text)
            received_lang.append(lang)

        client = SarvamRealtimeSTTClient(
            api_key="test_api_key_123",
            language_code="hi-IN",
            model="saaras:v3-realtime",
            encoding="mulaw",
            sample_rate=8000,
            on_final_transcript=on_final
        )

        mock_ws = AsyncMock()
        mock_messages = [
            json.dumps({"event": "session.begin", "request_id": "req-hi-200"}),
            json.dumps({"event": "transcript.final", "utterance_idx": 0, "text": "नमस्ते, क्या आपके पास 3 किलोवाट का सोलर सिस्टम है?", "language": "hi-IN"}),
        ]

        async def mock_iter():
            for m in mock_messages:
                yield m

        mock_ws.__aiter__.side_effect = mock_iter

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            await client.connect()
            await client.send_audio_chunk(dummy_mulaw_8k_chunk)
            await asyncio.sleep(0.05)
            await client.close()

        assert len(received_final) == 1
        assert "सोलर सिस्टम" in received_final[0]
        assert received_lang[0] == "hi-IN"

    asyncio.run(_run())


# ==============================================================================
# TEST 4: 8kHz μ-law → Saaras v3 realtime → English transcript
# ==============================================================================
def test_4_english_transcript_pipeline(dummy_mulaw_8k_chunk):
    """Verify Indian English speech recognition event handling."""
    async def _run():
        received_final = []

        def on_final(text, lang):
            received_final.append(text)

        client = SarvamRealtimeSTTClient(
            api_key="test_api_key_123",
            language_code="en-IN",
            model="saaras:v3-realtime",
            encoding="mulaw",
            sample_rate=8000,
            on_final_transcript=on_final
        )

        mock_ws = AsyncMock()
        mock_messages = [
            json.dumps({"event": "session.begin", "request_id": "req-en-300"}),
            json.dumps({"event": "transcript.final", "utterance_idx": 0, "text": "Hello, can you explain the government subsidy for rooftop solar?", "language": "en-IN"}),
        ]

        async def mock_iter():
            for m in mock_messages:
                yield m

        mock_ws.__aiter__.side_effect = mock_iter

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            await client.connect()
            await client.send_audio_chunk(dummy_mulaw_8k_chunk)
            await asyncio.sleep(0.05)
            await client.close()

        assert len(received_final) == 1
        assert "government subsidy" in received_final[0]

    asyncio.run(_run())


# ==============================================================================
# TEST 5: Telugu + English code-mixed speech (Tenglish)
# ==============================================================================
def test_5_tenglish_code_mixed_pipeline():
    """Verify code-mixed Telugu + English (Tenglish) is captured and preserves intent."""
    async def _run():
        received_final = []

        def on_final(text, lang):
            received_final.append(text)

        client = SarvamRealtimeSTTClient(
            api_key="test_api_key_123",
            language_code="auto",
            model="saaras:v3-realtime",
            on_final_transcript=on_final
        )

        mock_ws = AsyncMock()
        tenglish_input = "Sir, naaku 3 kilowatt solar panels price entha padutundi? Subsidy undha?"
        mock_messages = [
            json.dumps({"event": "session.begin", "request_id": "req-teng-400"}),
            json.dumps({"event": "transcript.final", "utterance_idx": 0, "text": tenglish_input, "language": "te-IN"}),
        ]

        async def mock_iter():
            for m in mock_messages:
                yield m

        mock_ws.__aiter__.side_effect = mock_iter

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            await client.connect()
            await asyncio.sleep(0.05)
            await client.close()

        assert len(received_final) == 1
        transcript = received_final[0]
        verticals = DynamicKnowledgeEngine.detect_verticals(transcript)
        assert "solar" in verticals

    asyncio.run(_run())


# ==============================================================================
# TEST 6: Hindi + English code-mixed speech (Hinglish)
# ==============================================================================
def test_6_hinglish_code_mixed_pipeline():
    """Verify code-mixed Hindi + English (Hinglish) is captured and preserves intent."""
    async def _run():
        received_final = []

        def on_final(text, lang):
            received_final.append(text)

        client = SarvamRealtimeSTTClient(
            api_key="test_api_key_123",
            language_code="auto",
            model="saaras:v3-realtime",
            on_final_transcript=on_final
        )

        mock_ws = AsyncMock()
        hinglish_input = "Bhaiya, kya solar installation ke liye bank loan aur EMI facility available hai?"
        mock_messages = [
            json.dumps({"event": "session.begin", "request_id": "req-hing-500"}),
            json.dumps({"event": "transcript.final", "utterance_idx": 0, "text": hinglish_input, "language": "hi-IN"}),
        ]

        async def mock_iter():
            for m in mock_messages:
                yield m

        mock_ws.__aiter__.side_effect = mock_iter

        with patch("websockets.connect", AsyncMock(return_value=mock_ws)):
            await client.connect()
            await asyncio.sleep(0.05)
            await client.close()

        assert len(received_final) == 1
        transcript = received_final[0]
        verticals = DynamicKnowledgeEngine.detect_verticals(transcript)
        assert "solar" in verticals
        assert "finance" in verticals

    asyncio.run(_run())


# ==============================================================================
# TEST 7: Customer interruption while AI audio is playing (Barge-in / clearAudio)
# ==============================================================================
def test_7_barge_in_interruption_flow():
    """
    Verify that when customer speech starts (VAD or partial), Plivo clearAudio is
    immediately dispatched and active TTS / LLM tasks are cancelled.
    """
    async def _run():
        mock_plivo_ws = AsyncMock()
        barge_in_controller = PlivoBargeInController(plivo_ws=mock_plivo_ws)

        # Simulate AI currently speaking
        barge_in_controller.is_ai_speaking = True

        # Create dummy in-flight TTS and LLM tasks
        async def dummy_tts_stream():
            await asyncio.sleep(5)

        async def dummy_llm_stream():
            await asyncio.sleep(5)

        barge_in_controller.active_tts_task = asyncio.create_task(dummy_tts_stream())
        barge_in_controller.active_llm_task = asyncio.create_task(dummy_llm_stream())

        # Customer starts speaking -> trigger barge-in
        await barge_in_controller.on_user_speech_detected()

        # 1. AI speaking state must be cleared
        assert barge_in_controller.is_ai_speaking is False

        # 2. Plivo must receive clearAudio event
        mock_plivo_ws.send_text.assert_called_once()
        sent_payload = json.loads(mock_plivo_ws.send_text.call_args[0][0])
        assert sent_payload.get("event") == "clearAudio"

        # 3. In-flight tasks must be cancelled
        assert barge_in_controller.active_tts_task is None or barge_in_controller.active_tts_task.cancelled()
        assert barge_in_controller.active_llm_task is None or barge_in_controller.active_llm_task.cancelled()

    asyncio.run(_run())


# ==============================================================================
# BONUS TEST: Dynamic Cross-Vertical Knowledge Retrieval (No Segment Lock)
# ==============================================================================
def test_dynamic_cross_vertical_knowledge_retrieval():
    """
    Verify that even if campaign/test started on segment='solar', customer asking about
    Property or EV dynamically retrieves approved Property/EV catalogue records.
    """
    mock_db = MagicMock()
    # Mock catalogue records in DB across multiple verticals
    mock_db.execute.return_value.fetchall.return_value = [
        (1, "Solar", "Rooftop", "3kW Tata Solar Panel", "Tata Power 3kW on-grid solar system with ₹78,000 MNRE subsidy"),
        (2, "Property", "Plots", "Bhimili Ocean View Plots", "Approved RERA residential villa plots in Bhimili from ₹15,000/sq.yd"),
        (3, "EV", "Two Wheeler", "Electric Scooter 120km Range", "High speed electric scooter with dual removable lithium batteries"),
        (4, "Finance", "Loans", "SBI Solar Loan & CIBIL Terms", "Minimum CIBIL 650 required, interest rate 7.5% p.a. with zero prepayment"),
    ]

    # Starting segment is Solar, but customer asks about Property
    customer_q1 = "Do you also have residential villa plots in Bhimili?"
    results1, direct_match1 = DynamicKnowledgeEngine.retrieve_approved_knowledge(
        mock_db, company_id=1, question=customer_q1, active_segment="Solar"
    )
    assert direct_match1 is True
    assert len(results1) > 0
    assert results1[0]["segment"] == "Property"
    assert "Bhimili" in results1[0]["title"]

    # Customer then asks about EV
    customer_q2 = "What about electric scooters and battery range?"
    results2, direct_match2 = DynamicKnowledgeEngine.retrieve_approved_knowledge(
        mock_db, company_id=1, question=customer_q2, active_segment="Solar"
    )
    assert direct_match2 is True
    assert results2[0]["segment"] == "EV"

    # Customer asks about Finance
    customer_q3 = "What is the CIBIL score required for the loan?"
    results3, direct_match3 = DynamicKnowledgeEngine.retrieve_approved_knowledge(
        mock_db, company_id=1, question=customer_q3, active_segment="Solar"
    )
    assert direct_match3 is True
    assert results3[0]["segment"] == "Finance"
    assert "CIBIL" in results3[0]["title"]


def test_webhook_voice_select_stream_xml():
    """Verify webhook_voice_select returns Plivo <Stream> when stream=1 and Sarvam is configured."""
    from app.api.v1.endpoints.staff_ai_calling import webhook_voice_select
    from starlette.datastructures import FormData
    import asyncio
    from unittest.mock import MagicMock, patch

    async def _run():
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None

        req = MagicMock()
        async def fake_form():
            return FormData({"CallUUID": "call_123_stream", "From": "+918031728899", "To": "+919876543210"})
        req.form = fake_form
        req.query_params = {"stream": "1"}
        req.headers = {"user-agent": "Plivo-Voice-Callback", "host": "www.myntreal.com"}
        req.url.scheme = "https"

        with patch("app.api.v1.endpoints.staff_ai_calling.get_sarvam_api_key", return_value="sk_test_key_123"):
            resp = await webhook_voice_select(
                request=req,
                log_id=999,
                lang="te",
                campaign_id=0,
                is_test=1,
                provider="plivo",
                db=db,
            )
            assert resp.status_code == 200
            assert resp.media_type == "application/xml"
            xml_str = resp.body.decode("utf-8")
            assert "<Stream" in xml_str
            assert 'bidirectional="true"' in xml_str
            assert 'contentType="audio/x-mulaw;rate=8000"' in xml_str
            assert "/api/v1/staff/ai-calling/stream/999" in xml_str

    asyncio.run(_run())


def test_first_time_caller_inbound_ivr():
    """Verify first-time inbound caller gets Telugu Female IVR menu with GetInput speech/dtmf."""
    from app.api.v1.endpoints.staff_ai_calling import webhook_voice_select
    from starlette.datastructures import FormData
    import asyncio
    from unittest.mock import MagicMock, patch

    async def _run():
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None  # No matching lead

        req = MagicMock()
        async def fake_form():
            return FormData({"CallUUID": "call_inbound_first", "From": "+919988776655", "To": "+918031728899"})
        req.form = fake_form
        req.query_params = {}
        req.headers = {"user-agent": "Plivo-Voice-Callback", "host": "www.myntreal.com"}
        req.url.scheme = "https"

        with patch("app.api.v1.endpoints.staff_ai_calling.get_sarvam_api_key", return_value="sk_test_key_123"):
            resp = await webhook_voice_select(
                request=req,
                log_id=None,  # Inbound call
                lang="te",
                campaign_id=0,
                is_test=0,
                provider="plivo",
                db=db,
            )
            assert resp.status_code == 200
            assert resp.media_type == "application/xml"
            xml_str = resp.body.decode("utf-8")
            assert "<GetInput" in xml_str
            assert 'inputType="speech dtmf"' in xml_str
            assert "te_ivr_menu.wav" in xml_str
            assert "ivr-choice" in xml_str

    asyncio.run(_run())


def test_returning_caller_ivr_bypass():
    """Verify returning caller with saved preferences bypasses IVR and connects straight to <Stream>."""
    from app.api.v1.endpoints.staff_ai_calling import webhook_voice_select
    from starlette.datastructures import FormData
    import asyncio
    from unittest.mock import MagicMock, patch

    async def _run():
        db = MagicMock()
        # Matched lead with Telugu and solar preferences
        db.execute.return_value.fetchone.return_value = (42, "Kari", "solar", "rooftop", "te", "Vidya", "Female", 1)

        req = MagicMock()
        async def fake_form():
            return FormData({"CallUUID": "call_inbound_returning", "From": "+919988776655", "To": "+918031728899"})
        req.form = fake_form
        req.query_params = {}
        req.headers = {"user-agent": "Plivo-Voice-Callback", "host": "www.myntreal.com"}
        req.url.scheme = "https"

        with patch("app.api.v1.endpoints.staff_ai_calling.get_sarvam_api_key", return_value="sk_test_key_123"):
            resp = await webhook_voice_select(
                request=req,
                log_id=None,
                lang="te",
                campaign_id=0,
                is_test=0,
                provider="plivo",
                db=db,
            )
            assert resp.status_code == 200
            xml_str = resp.body.decode("utf-8")
            # Should directly return Stream, skipping GetInput IVR
            assert "<Stream" in xml_str
            assert "<GetInput" not in xml_str

    asyncio.run(_run())


def test_webhook_ivr_choice_and_preference_save():
    """Verify webhook_ivr_choice processes choice, remembers preference in CRM, and returns Stream."""
    from app.api.v1.endpoints.staff_ai_calling import webhook_ivr_choice
    from starlette.datastructures import FormData
    import asyncio
    from unittest.mock import MagicMock

    async def _run():
        db = MagicMock()
        db.execute.return_value.scalar.return_value = 101  # lead_id
        db.execute.return_value.fetchone.return_value = None

        req = MagicMock()
        async def fake_form():
            return FormData({"CallUUID": "call_choice_1", "From": "+919988776655", "Digits": "1"})
        req.form = fake_form
        req.query_params = {}
        req.headers = {"user-agent": "Plivo-Voice-Callback", "host": "www.myntreal.com"}
        req.url.scheme = "https"

        resp = await webhook_ivr_choice(request=req, log_id=888, db=db)
        assert resp.status_code == 200
        xml_str = resp.body.decode("utf-8")
        assert "<Stream" in xml_str
        assert "/api/v1/staff/ai-calling/stream/888" in xml_str

    asyncio.run(_run())


def test_conversational_filler_engine_caching():
    """Verify ConversationalFillerEngine phrases and cache behavior."""
    from app.services.sarvam_telephony_adapter import ConversationalFillerEngine

    te_female = ConversationalFillerEngine.get_filler_text("te", "kavya")
    assert "తప్పకుండా" in te_female
    assert "వివరాలు" in te_female

    hi_male = ConversationalFillerEngine.get_filler_text("hi", "shubh")
    assert "ज़रूर" in hi_male
    assert "देता हूँ" in hi_male

    hi_female = ConversationalFillerEngine.get_filler_text("hi", "kavya")
    assert "देती हूँ" in hi_female


