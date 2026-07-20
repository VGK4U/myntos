"""
AI Calling Campaign Manager — Backend Endpoint
DC Protocol: AI_CALLING_001

Architecture:
  - Twilio: outbound calls + speech-to-text via Gather (hi-IN, te-IN, en-IN)
  - OpenAI GPT-4o: conversation logic + post-call summarization
  - OpenAI TTS (tts-1): voice response generation (multilingual)
  - Product Catalogue: injected into GPT system prompt as per-segment knowledge base

Tables (created in main.py startup):
  ai_campaigns, ai_campaign_staff, ai_call_logs, ai_call_sessions, ai_product_catalogue
  crm_leads: additive nullable AI columns (ai_last_called_at, ai_call_count, ai_campaign_id,
             ai_status, ai_summary, ai_language)

Zero changes to existing dialer, CRM, or any other feature.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Query, Body
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_, and_
from typing import Optional, List
from datetime import datetime, timedelta
from urllib.parse import quote as _urlquote
import pytz
import json
import logging
import os
import hashlib
import uuid
import asyncio
import random as _random
from collections import defaultdict as _defaultdict

from app.core.database import get_db
from app.core.database import SessionLocal as _SessionLocal
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.models.staff import StaffEmployee
from app.models.crm import CRMLead

logger = logging.getLogger(__name__)
router = APIRouter()

IST = pytz.timezone('Asia/Kolkata')

TWILIO_SID   = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.environ.get("TWILIO_PHONE_NUMBER", "")
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

AI_AUDIO_DIR = "/tmp/ai_audio"
os.makedirs(AI_AUDIO_DIR, exist_ok=True)

# ── Engagement filler phrases (spoken while GPT is thinking) ──────────────────
# Pre-generated using OpenAI TTS so they sound exactly like Vidya's voice.
# Loaded lazily on first call per language; multiple phrases for variety.
_FILLER_PHRASES = {
    "hi": [
        "Haan ji, ek pal mein batati hoon...",
        "Bilkul, abhi dekhti hoon...",
        "Ji zaroor, ek second...",
    ],
    "te": [
        "Avunu, okka nimisham cheppataanu...",
        "Sure, oka second...",
        "Ji, tappakunda cheppataanu...",
    ],
    "en": [
        "Sure, just a moment...",
        "Of course, let me check that for you...",
        "Absolutely, one second...",
    ],
}
_FILLER_CACHE: dict = {}   # lang -> [wav_filename, ...]
_FILLER_GENERATING: set = set()  # langs currently being generated

def _warm_filler_cache_startup():
    """Pre-generate filler phrases for all languages at module load.

    Runs in a daemon thread so it doesn't block startup.
    After ~15s the cache is warm and no call will fall back to Polly.Aditi.
    """
    import time as _time
    _time.sleep(4)  # let FastAPI finish startup before hitting OpenAI
    for _lang in ("hi", "te", "en"):
        try:
            _ensure_fillers_sync(_lang)
        except Exception:
            pass

import threading as _threading
_threading.Thread(target=_warm_filler_cache_startup, daemon=True).start()

# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------

def _detect_lang(text: str) -> str:
    """Detect spoken language from Unicode script ranges in transcribed text.
    Returns 'te' (Telugu), 'hi' (Hindi/Devanagari), or 'en' (default).
    """
    for ch in text:
        cp = ord(ch)
        if 0x0C00 <= cp <= 0x0C7F:   # Telugu script
            return "te"
        if 0x0900 <= cp <= 0x097F:   # Devanagari (Hindi / Marathi / etc.)
            return "hi"
    return "en"

# Phrases in GPT's reply that indicate it could NOT answer the customer's question
_UNCERTAINTY_PHRASES = [
    "abhi nahi hai", "mere paas nahi", "confirm karke", "check karke",
    "pata nahi", "nahi pata", "don't have", "don't know", "do not have",
    "not available", "not sure", "i'm not sure", "i am not sure",
    "i cannot", "i can't", "chalega confirm", "baar batata", "baar batati",
    "baar bataenge", "more information", "verify kar", "verify karna",
    "verify karke", "specific detail", "abhi confirm", "abhi check",
    "నాకు తెలియదు", "నాకు సమాచారం లేదు", "confirm చేసి",
]

def _is_uncertain(reply: str) -> bool:
    """Return True if the AI reply signals it could not fully answer."""
    lower = reply.lower()
    return any(p.lower() in lower for p in _UNCERTAINTY_PHRASES)

def _extract_customer_question(conversation: list) -> str:
    """Return the last customer message (the unanswered question)."""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            return msg.get("content", "").strip()
    return ""


def _ensure_fillers_sync(lang: str):
    """Generate filler audio files for a language (sync, runs in thread pool)."""
    if lang in _FILLER_CACHE or lang in _FILLER_GENERATING:
        return
    _FILLER_GENERATING.add(lang)
    try:
        phrases = _FILLER_PHRASES.get(lang, _FILLER_PHRASES["hi"])
        files = []
        for p in phrases:
            try:
                fname = _generate_tts(p, lang)
                # Only cache if the file was actually written to disk
                if fname and os.path.exists(os.path.join(AI_AUDIO_DIR, fname)) and os.path.getsize(os.path.join(AI_AUDIO_DIR, fname)) > 0:
                    files.append(fname)
            except Exception:
                pass
        if files:
            _FILLER_CACHE[lang] = files
    finally:
        _FILLER_GENERATING.discard(lang)

# ── Voice settings cache ──────────────────────────────────────────────────────
VALID_VOICES = ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]
_VOICE_CACHE: dict = {}  # company_id -> voice name


def _get_company_voice(db: Session, company_id: int) -> str:
    """Return the saved TTS voice for a company (default: nova)."""
    if company_id in _VOICE_CACHE:
        return _VOICE_CACHE[company_id]
    try:
        row = db.execute(
            text("SELECT value FROM ai_settings WHERE company_id=:cid AND key='voice'"),
            {"cid": company_id},
        ).fetchone()
        voice = row[0] if row and row[0] in VALID_VOICES else "nova"
    except Exception:
        voice = "nova"
    _VOICE_CACHE[company_id] = voice
    return voice


LANG_MAP = {
    "hi": "hi-IN",
    "te": "te-IN",
    "en": "en-IN",
}
LANG_LABEL = {"hi": "Hindi", "te": "Telugu", "en": "English"}

QUALIFIED_OUTCOMES  = {"qualified", "interested", "callback"}
NEGATIVE_OUTCOMES   = {"not_interested", "do_not_call", "wrong_number"}

FULL_ACCESS_ROLES = {"vgk4u", "key_leadership", "leadership_role", "ea", "hr"}


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def get_ist_now():
    return datetime.now(IST).replace(tzinfo=None)


def _webhook_base(request: Request) -> str:
    # DC Protocol: In Replit production deployments REPL_DEPLOYMENT is set; always use
    # canonical public domain so webhook/share URLs are never the worf.replit.dev dev domain.
    if os.environ.get("REPL_DEPLOYMENT") or os.environ.get("PROD_DATABASE_URL"):
        return "https://mnrteam.com"
    # Dev: prefer the Replit preview domain so webhooks reach the running server
    dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if dev_domain:
        return f"https://{dev_domain}"
    return str(request.base_url).rstrip("/")


def _twilio_client():
    if not TWILIO_SID or not TWILIO_TOKEN:
        raise HTTPException(status_code=503, detail="Twilio credentials not configured")
    from twilio.rest import Client
    return Client(TWILIO_SID, TWILIO_TOKEN)


def _naturalise_tts_text(text: str, language: str = "hi") -> str:
    """Make GPT reply sound more human before sending to TTS.
    - Strips meta-tokens like [END_CALL] [CALLBACK]
    - Adds breath pauses at sentence boundaries
    - Ensures 'Vidya' is always spoken with a clear pause on each side
    - Injects natural affirmation fillers so the voice doesn't feel robotic
    """
    import re
    # Remove control tokens — they must not be spoken
    text = re.sub(r'\[(END_CALL|CALLBACK|end_call|callback)\]', '', text).strip()
    # Collapse multiple spaces / newlines
    text = re.sub(r'\s+', ' ', text)

    # Ensure agent names always get a micro-pause on each side so the name is clear
    # Replace bare "Vidya" or "Karthik" (not already surrounded by punctuation/ellipsis)
    text = re.sub(r'(?<![.,…])\bVidya\b(?![.,…])', '... Vidya,', text)
    text = re.sub(r'(?<![.,…])\bKarthik\b(?![.,…])', '... Karthik,', text)
    # Clean up any double-pause artefacts introduced by the greeting template
    text = re.sub(r'\.{3}\s*\.\.\.\s*Vidya,', '... Vidya,', text)
    text = re.sub(r'\.{3}\s*\.\.\.\s*Karthik,', '... Karthik,', text)

    # Vizag → Visakhapatnam so TTS pronounces it correctly
    text = re.sub(r'\bVizag\b', 'Visakhapatnam', text, flags=re.IGNORECASE)

    if language == "hi":
        # In Hindi speech, "..." maps to a natural breath pause in OpenAI TTS
        text = re.sub(r'(?<=[।!?])\s+', '… ', text)
        # If the reply starts immediately with a fact/number, add a warm opener
        if re.match(r'^\d', text):
            text = "Haan ji, " + text
    elif language == "te":
        text = re.sub(r'(?<=[!?।])\s+', '… ', text)
    else:  # English
        text = re.sub(r'(?<=[.!?])\s+', '... ', text)

    return text.strip()


def _ffmpeg_to_mulaw(raw_path: str, filepath: str) -> None:
    """Convert any PCM WAV to G.711 µ-law 8kHz mono — the native PSTN codec."""
    import subprocess
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", raw_path,
            "-af", "loudnorm=I=-16:TP=-2:LRA=11",  # gentle loudness, natural dynamics
            "-ar", "8000",                           # 8 kHz — G.711 standard
            "-ac", "1",                              # mono
            "-acodec", "pcm_mulaw",                  # G.711 µ-law
            filepath,
        ],
        capture_output=True, timeout=20,
    )
    try:
        os.remove(raw_path)
    except Exception:
        pass
    if result.returncode != 0 or not os.path.exists(filepath):
        try:
            os.rename(raw_path, filepath)
        except Exception:
            pass


def _google_tts(text: str, language: str, is_male: bool = False) -> bytes | None:
    """
    Call Google Cloud Text-to-Speech REST API.
    Returns raw LINEAR16 WAV bytes, or None on failure.

    Voice selection — native speakers per language:
      te-IN → te-IN-Standard-A (female) / te-IN-Standard-B (male)
      hi-IN → hi-IN-Neural2-D (female) / hi-IN-Neural2-B (male)
      en-IN → falls back to OpenAI (not handled here)

    Requires Cloud TTS API to be enabled at:
      https://console.cloud.google.com/apis/api/texttospeech.googleapis.com
    """
    import httpx, base64
    GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "")
    if not GOOGLE_KEY or language not in ("hi", "te"):
        return None

    lang_code_map = {"hi": "hi-IN", "te": "te-IN"}
    # Female voices: neural2 for Hindi (sounds very natural), standard for Telugu
    # Male voices: neural2 for Hindi, standard for Telugu
    voice_name_map = {
        "hi": ("hi-IN-Neural2-D", "hi-IN-Neural2-B"),  # (female, male) — Neural2 = highest quality
        "te": ("te-IN-Standard-A", "te-IN-Standard-B"), # Telugu only has Standard tier
    }
    lang_code = lang_code_map[language]
    female_voice, male_voice = voice_name_map[language]
    voice_name = male_voice if is_male else female_voice

    try:
        resp = httpx.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_KEY}",
            json={
                "input": {"text": text},
                "voice": {
                    "languageCode": lang_code,
                    "name": voice_name,
                    "ssmlGender": "MALE" if is_male else "FEMALE",
                },
                "audioConfig": {
                    "audioEncoding": "LINEAR16",
                    "sampleRateHertz": 24000,
                    "speakingRate": 0.95,  # slightly measured pace, natural
                    "pitch": 0.0,
                    "volumeGainDb": 1.0,
                },
            },
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            audio_bytes = base64.b64decode(data.get("audioContent", ""))
            logger.info(f"[GTTS] ✅ {voice_name} lang={language} male={is_male} bytes={len(audio_bytes)}")
            return audio_bytes
        else:
            logger.warning(f"[GTTS] API error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        logger.warning(f"[GTTS] Exception: {e}")
        return None


def _generate_tts(text_content: str, language: str = "hi", voice_override: str = None) -> str:
    """Generate TTS audio, convert to G.711 µ-law WAV for phone delivery.

    Engine: OpenAI TTS HD (tts-1-hd) — shimmer for hi/te, nova for en.

    Audio pipeline:
      Raw PCM WAV (24 kHz) → ffmpeg → loudnorm → 8 kHz G.711 µ-law WAV
    """
    if not OPENAI_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    import httpx, subprocess, struct

    # OpenAI voice selection
    if voice_override and voice_override in VALID_VOICES:
        oai_voice = voice_override
    else:
        voice_map = {"hi": "shimmer", "te": "shimmer", "en": "nova"}
        oai_voice = voice_map.get(language, "shimmer")

    # Pre-process text for natural delivery
    clean_text = _naturalise_tts_text(text_content, language)
    if not clean_text:
        clean_text = text_content

    filename = f"{uuid.uuid4().hex}.wav"
    filepath  = os.path.join(AI_AUDIO_DIR, filename)
    raw_path  = filepath + ".raw.wav"

    # ── OpenAI TTS HD ───────────────────────────────────────────────────────────
    resp = httpx.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": "tts-1-hd", "input": clean_text, "voice": oai_voice,
              "speed": 0.95, "response_format": "wav"},
        timeout=30,
    )
    resp.raise_for_status()
    with open(raw_path, "wb") as f:
        f.write(resp.content)

    _ffmpeg_to_mulaw(raw_path, filepath)
    return filename


def _gpt_conversation(messages: list, system_prompt: str, language: str = "hi") -> tuple:
    """Call GPT-4o with conversation history.

    Returns (reply_text, prompt_tokens, completion_tokens).
    Token counts are 0 on fallback/error.
    """
    _fallbacks = {
        "hi": "नमस्ते! मैं मिंटरियल प्रॉपर्टीज़ से बोल रहा हूं। आपकी प्रॉपर्टी में रुचि के बारे में हम जल्द संपर्क करेंगे।",
        "te": "నమస్కారం! మేను Myntreal Properties నుండి మాట్లాడుతున్నాం. మీకు త్వరలో సంప్రదిస్తాం.",
        "en": "Hello! This is Myntreal Properties calling. Our team will be in touch with you shortly regarding your property interest.",
    }
    fallback = _fallbacks.get(language, _fallbacks["en"])

    if not OPENAI_KEY:
        return fallback, 0, 0
    import httpx
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 180,
        "temperature": 0.75,
    }
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        return reply, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[AI-CALLING] OpenAI GPT error: {e}")
        return fallback, 0, 0


# OpenAI pricing (USD) — update if pricing changes
_GPT4O_INPUT_PER_TOKEN  = 2.50 / 1_000_000   # $2.50 per 1M input tokens
_GPT4O_OUTPUT_PER_TOKEN = 10.0 / 1_000_000   # $10.00 per 1M output tokens
_TTS_HD_PER_CHAR        = 15.0 / 1_000_000   # $15.00 per 1M characters (tts-1)
# Twilio outbound India: ~$0.0085/min (carrier + Twilio blended estimate)
_TWILIO_PER_MIN_USD     = 0.0085


def _log_usage(db: Session, company_id: int, log_id: int | None,
               event_type: str, model: str, input_tok: int = 0,
               output_tok: int = 0, chars: int = 0, source: str = "gpt"):
    """Insert one row into ai_usage_log. Silent on failure."""
    if event_type == "gpt4o_call":
        cost = input_tok * _GPT4O_INPUT_PER_TOKEN + output_tok * _GPT4O_OUTPUT_PER_TOKEN
    elif event_type == "tts_generation":
        cost = chars * _TTS_HD_PER_CHAR
    else:
        cost = 0.0
    try:
        db.execute(text("""
            INSERT INTO ai_usage_log
              (company_id, log_id, event_type, model, input_tokens, output_tokens,
               characters, source, estimated_cost_usd)
            VALUES
              (:cid, :lid, :et, :model, :it, :ot, :chars, :src, :cost)
        """), {"cid": company_id, "lid": log_id, "et": event_type, "model": model,
               "it": input_tok, "ot": output_tok, "chars": chars,
               "src": source, "cost": cost})
        db.commit()
    except Exception:
        pass


# ── KB-first answering ──────────────────────────────────────────────────────────
# Common stopwords in all 3 supported languages (word-level, not script-aware)
_STOPWORDS = {
    # English
    "a","an","the","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall","can",
    "i","we","you","he","she","it","they","this","that","these","those","what",
    "which","who","when","where","how","why","and","or","but","if","for","with",
    "about","from","to","of","in","on","at","by","as","so","me","my","our","your",
    "his","her","their","its","us","them","any","all","each","more","also","not",
    # Hindi transliteration (common in Twilio STT output)
    "hai","hain","ho","tha","the","thi","kya","ka","ki","ke","ko","koi","kuch",
    "aur","ya","par","mein","se","ne","bhi","sirf","toh","phir","agar","jab",
    "lekin","kyunki","yeh","woh","main","hum","aap","unhe","iske","uske","jo",
    "ab","abhi","tab","wahan","yahan","kab","kaise","itna","bahut","ek","do",
    # Telugu transliteration
    "undi","oka","meeru","nenu","memu","varu","adi","ivi","avunu","kadu","leda",
    "lo","ki","ku","tho","ni","la","ga","ante","ite","ayithe","cheppandi",
}

import re as _re

def _kb_direct_answer(
    db: Session, company_id: int, question: str,
    segment: str = "", language: str = "hi"
) -> tuple[str | None, str | None]:
    """Try to answer directly from KB without calling GPT.

    Returns (answer_text, entry_title) if a confident match is found, else (None, None).
    Confidence threshold: at least 2 keyword overlaps and score >= 0.12.
    This saves one GPT-4o call (~$0.003) for straightforward factual questions.
    """
    if not question or len(question.strip()) < 5:
        return None, None

    # Fetch active KB entries
    q_sql = """
        SELECT title, content, category
        FROM ai_product_catalogue
        WHERE company_id=:cid AND is_active=TRUE
    """
    params: dict = {"cid": company_id}
    if segment:
        q_sql += " AND segment=:seg"
        params["seg"] = segment
    rows = db.execute(text(q_sql), params).fetchall()
    if not rows:
        return None, None

    # Tokenise the question
    q_norm  = _re.sub(r'[^\w\s]', ' ', question.lower())
    q_words = set(q_norm.split()) - _STOPWORDS
    if not q_words:
        return None, None

    # Extract any long words (≥5 chars) — likely brand names, project names, key terms
    key_terms = {w for w in q_words if len(w) >= 5}

    best_score = 0.0
    best_overlap = 0
    best_content = None
    best_title   = None

    for row in rows:
        title   = (row[0] or '').lower()
        content = (row[1] or '').lower()
        combined = _re.sub(r'[^\w\s]', ' ', f"{title} {content}")
        entry_words = set(combined.split()) - _STOPWORDS
        if not entry_words:
            continue
        overlap = len(q_words & entry_words)
        score   = overlap / max(len(q_words), 1)
        # Brand/project name match: if any long key term appears in the entry → instant match
        brand_hit = bool(key_terms) and any(kt in combined for kt in key_terms)
        if brand_hit:
            # Boost overlap for brand/project name hits
            overlap = max(overlap, 2)
            score   = max(score, 0.20)
        if overlap > best_overlap or (overlap == best_overlap and score > best_score):
            best_overlap = overlap
            best_score   = score
            best_content = row[1]
            best_title   = row[0]

    # Require at least 2 matching keywords AND a similarity score ≥ 12%
    # Single strong brand-name match also qualifies (overlap was boosted above)
    if best_overlap >= 2 and best_score >= 0.12 and best_content:
        return best_content, best_title

    return None, None


async def _bg_gpt_tts(log_id: int, conversation: list, system_prompt: str, lang: str):
    """Background task: KB-first → GPT fallback → TTS → store in ai_call_sessions.

    Pipeline:
      1. Extract the customer's last question.
      2. Try to answer directly from the Knowledge Base (no GPT credit used).
      3. If KB gives a confident answer → use it directly (saves GPT tokens).
      4. If no KB match → call GPT-4o → log token usage.
      5. Generate TTS for the final reply → log TTS character usage.
      6. Store audio URL in ai_call_sessions so /webhook/poll can serve it.
    """
    loop = asyncio.get_event_loop()
    db = _SessionLocal()
    try:
        # ── Resolve company + agent voice for this call ───────────────────────
        company_row = db.execute(
            text("SELECT company_id FROM ai_call_logs WHERE id=:lid"), {"lid": log_id}
        ).fetchone()
        cid = company_row[0] if company_row else 4
        # Agent voice from session overrides company default (set by voice-select at call start)
        sess_voice_row = db.execute(
            text("SELECT agent_voice FROM ai_call_sessions WHERE log_id=:lid"), {"lid": log_id}
        ).fetchone()
        if sess_voice_row and sess_voice_row[0] and sess_voice_row[0] in VALID_VOICES:
            voice = sess_voice_row[0]
        else:
            voice = _get_company_voice(db, cid)

        # ── Step 1: Try KB-first answer ───────────────────────────────────────
        customer_q  = _extract_customer_question(conversation)
        kb_answer, kb_title = None, None
        if customer_q:
            kb_answer, kb_title = await loop.run_in_executor(
                None, lambda: _kb_direct_answer(db, cid, customer_q, language=lang)
            )

        # ── Step 2: Choose reply source ───────────────────────────────────────
        if kb_answer:
            # Direct KB hit — no GPT call, no GPT credits spent
            reply_clean = kb_answer.strip()
            end_call    = False
            callback    = False
            _log_usage(db, cid, log_id, "kb_hit", "knowledge_base", source="kb")
            logger.info(f"[AI-CALLING] KB hit for log {log_id} — KB entry: '{kb_title}'")
        else:
            # No KB match → call GPT-4o
            reply_raw, prompt_tok, completion_tok = await loop.run_in_executor(
                None, lambda: _gpt_conversation(conversation, system_prompt, language=lang)
            )
            end_call    = "[END_CALL]" in reply_raw
            callback    = "[CALLBACK]"  in reply_raw
            reply_clean = reply_raw.replace("[END_CALL]", "").replace("[CALLBACK]", "").strip()
            # Log GPT token usage
            if prompt_tok or completion_tok:
                _log_usage(db, cid, log_id, "gpt4o_call", "gpt-4o",
                           input_tok=prompt_tok, output_tok=completion_tok, source="gpt")

        # ── Step 3: TTS ───────────────────────────────────────────────────────
        tts_chars = len(reply_clean)
        try:
            audio_file = await loop.run_in_executor(
                None, lambda: _generate_tts(reply_clean, lang, voice_override=voice)
            )
            # Verify the file was actually written to disk before treating as success
            if audio_file:
                audio_disk_check = os.path.join(AI_AUDIO_DIR, audio_file)
                if not os.path.exists(audio_disk_check) or os.path.getsize(audio_disk_check) == 0:
                    logger.error(f"[AI-CALLING] TTS returned filename {audio_file} but file is missing/empty on disk — treating as FALLBACK")
                    audio_file = None
            # Log TTS character usage
            if audio_file:
                _log_usage(db, cid, log_id, "tts_generation", "tts-1",
                           chars=tts_chars, source="kb" if kb_answer else "gpt")
        except Exception as tts_err:
            logger.error(f"[AI-CALLING] TTS generation failed for log {log_id}: {tts_err}")
            audio_file = None

        # ── Step 4: Store result ──────────────────────────────────────────────
        updated_conv = conversation + [{"role": "assistant", "content": reply_clean}]
        db.execute(text("""
            UPDATE ai_call_sessions
            SET next_audio_url = :af,
                next_reply_text = :rt,
                conversation    = :conv,
                updated_at      = NOW()
            WHERE log_id = :lid
        """), {
            "af":   audio_file or "FALLBACK",
            "rt":   reply_clean,
            "conv": json.dumps(updated_conv),
            "lid":  log_id,
        })
        db.execute(text(
            "UPDATE ai_call_logs SET transcript=:trans WHERE id=:id"
        ), {"trans": json.dumps(updated_conv), "id": log_id})

        # ── Step 4b: Detect rejection + log persuasion attempt in notes ───────
        _NOT_INTERESTED_PHRASES = [
            # Telugu
            "vaddhu", "vaddu", "avasaram ledu", "interest ledu", "vaddhu sir", "vaddhu madam",
            "abhi vaddhu", "ippudu vaddhu",
            # Hindi
            "nahi chahiye", "mujhe nahi chahiye", "interested nahi", "no interest",
            "zaroorat nahi", "abhi nahi",
            # English
            "not interested", "no thanks", "no thank you", "don't need", "not now",
            "please don't call", "remove my number",
        ]
        _customer_last_msg = ""
        for _m in reversed(conversation):
            if _m.get("role") == "user":
                _customer_last_msg = _m.get("content", "").lower()
                break
        _is_rejection = any(ph in _customer_last_msg for ph in _NOT_INTERESTED_PHRASES)
        if _is_rejection:
            # Count how many prior "not interested" messages exist in this conversation
            _prior_rejections = sum(
                1 for _m in conversation[:-1]
                if _m.get("role") == "user"
                and any(ph in _m.get("content", "").lower() for ph in _NOT_INTERESTED_PHRASES)
            )
            _rejection_num = _prior_rejections + 1
            _ist_now_str = get_ist_now().strftime("%d %b %Y %I:%M %p IST")
            if _rejection_num == 1:
                _note_text = f"[{_ist_now_str}] 🔄 Not interested (attempt 1) — AI asked for 2 min + pitched company benefits"
                _crm_note  = f"[{_ist_now_str}] AI call: Customer said not interested → AI made persuasion pitch (asked for 2 minutes + company benefits). Awaiting customer response."
            else:
                _note_text = f"[{_ist_now_str}] ❌ Not interested (firm, rejection #{_rejection_num}) — AI ended call politely"
                _crm_note  = f"[{_ist_now_str}] AI call: Customer firmly rejected (#{_rejection_num}) — call closed politely."
            try:
                # 1. Log to ai_call_logs.notes
                db.execute(text("""
                    UPDATE ai_call_logs
                    SET notes = CASE
                        WHEN notes IS NULL OR notes = '' THEN :note
                        ELSE notes || E'\\n' || :note
                    END
                    WHERE id = :lid
                """), {"note": _note_text, "lid": log_id})
                # 2. Also append to crm_leads.recent_comments if lead is linked
                _lead_row = db.execute(
                    text("SELECT lead_id FROM ai_call_logs WHERE id=:lid"), {"lid": log_id}
                ).fetchone()
                if _lead_row and _lead_row[0]:
                    db.execute(text("""
                        UPDATE crm_leads
                        SET recent_comments = CASE
                            WHEN recent_comments IS NULL OR recent_comments = '' THEN :cmt
                            ELSE :cmt || E'\\n' || recent_comments
                        END,
                        updated_at = NOW()
                        WHERE id = :leid
                    """), {"cmt": _crm_note, "leid": _lead_row[0]})
                logger.info(f"[AI-CALLING] Rejection #{_rejection_num} logged for call {log_id}")
            except Exception as _rj_err:
                logger.warning(f"[AI-CALLING] Could not log rejection note: {_rj_err}")

        # ── Step 5: Track unanswered questions ────────────────────────────────
        if not kb_answer and _is_uncertain(reply_clean) and customer_q:
            try:
                db.execute(text("""
                    INSERT INTO ai_unanswered_questions
                        (company_id, log_id, question, ai_reply, created_at)
                    SELECT company_id, :lid, :q, :ar, NOW()
                    FROM ai_call_logs WHERE id = :lid
                    ON CONFLICT DO NOTHING
                """), {"lid": log_id, "q": customer_q, "ar": reply_clean})
            except Exception:
                pass

        # ── Step 6: End-call signals ──────────────────────────────────────────
        turn_count = sum(1 for m in conversation if m.get("role") == "assistant")
        if (end_call or callback) and turn_count >= 3:
            end_status = "callback_pending" if callback else "end_call_pending"
            db.execute(text(
                "UPDATE ai_call_sessions SET status=:st WHERE log_id=:lid"
            ), {"st": end_status, "lid": log_id})

        db.commit()
    except Exception as bg_err:
        logger.error(f"[AI_CALLING] Background GPT/TTS failed for log {log_id}: {bg_err}")
        try:
            db.execute(text(
                "UPDATE ai_call_sessions SET next_audio_url='ERROR' WHERE log_id=:lid"
            ), {"lid": log_id})
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _gpt_summarize(transcript: list, language: str = "hi") -> dict:
    """Post-call: generate AI summary + extract full lead details from the conversation."""
    if not OPENAI_KEY or not transcript:
        return {"summary": "No transcript available.", "outcome": "no_answer",
                "detected_language": language}
    import httpx
    transcript_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in transcript
    )
    from datetime import date as _date
    today_str = _date.today().isoformat()
    prompt = f"""You are a CRM data extractor analyzing a real estate sales call transcript.
Today's date is {today_str}.
Transcript (may be in Hindi/Telugu/English):
{transcript_text}

Extract every detail the customer mentioned. If a field was not mentioned, use null.
Respond with valid JSON only — no extra text:
{{
  "outcome": "qualified|not_interested|callback|no_answer|do_not_call|wrong_number",
  "summary": "2-4 sentence summary of the entire call in English",
  "detected_language": "hi|te|en",
  "interest_level": "high|medium|low|none",
  "customer_name": "full name if mentioned, else null",
  "customer_phone": "phone number if mentioned, else null",
  "customer_email": "email if mentioned, else null",
  "city": "city of residence or interest if mentioned, else null",
  "location_preference": "preferred area/locality for property, else null",
  "property_type": "plot|apartment|villa|commercial|franchise|other or null",
  "budget_min": "minimum budget in numbers (no currency symbol), else null",
  "budget_max": "maximum budget in numbers (no currency symbol), else null",
  "requirements": "any specific requirements the customer mentioned, else null",
  "timeline": "when they plan to buy/invest, else null",
  "next_follow_up_date": "YYYY-MM-DD if they mentioned a specific callback date/time, else null",
  "notes": "any other important points — objections, questions, commitments made"
}}"""
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 500, "temperature": 0.1},
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    raw = raw.strip("```json").strip("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"summary": raw[:400], "outcome": "no_answer", "detected_language": language}


def _fetch_live_property_knowledge(db: Session) -> str:
    """Query rd_properties marketplace live — so Vidya always knows the current listings."""
    try:
        props = db.execute(text("""
            SELECT
                p.id, p.title, p.property_category,
                pt.name AS type_name,
                p.address, p.landmark, p.city, p.state,
                p.total_area, p.area_unit,
                p.bedrooms, p.bathrooms, p.total_floors,
                p.listed_price, p.price_per_unit, p.price_unit, p.price_on_request,
                p.discounted_price, p.booking_amount, p.is_negotiable,
                p.facing, p.road_width, p.plot_dimensions,
                p.possession_status, p.rera_number,
                p.description,
                p.contact_person_name, p.contact_person_phone
            FROM rd_properties p
            LEFT JOIN rd_property_types pt ON p.property_type_id = pt.id
            WHERE p.status = 'APPROVED'
            ORDER BY p.id
        """)).fetchall()

        if not props:
            return ""

        amenities_map: dict = {}
        for row in db.execute(text("""
            SELECT pa.property_id, a.name
            FROM rd_property_amenities pa
            JOIN rd_amenities a ON pa.amenity_id = a.id
            ORDER BY pa.property_id, a.name
        """)).fetchall():
            amenities_map.setdefault(row[0], []).append(row[1])

        lines = [
            "### LIVE PROPERTY LISTINGS — VGK Real Dreams Marketplace",
            "These are the ACTUAL properties currently available. Use ONLY these details — do not invent or assume any other property.\n",
        ]

        for p in props:
            (pid, title, category, type_name,
             address, landmark, city, state,
             total_area, area_unit,
             bedrooms, bathrooms, total_floors,
             listed_price, price_per_unit, price_unit, price_on_request,
             discounted_price, booking_amount, is_negotiable,
             facing, road_width, plot_dimensions,
             possession_status, rera_number,
             description,
             contact_name, contact_phone) = p

            lines.append(f"─── {title} ───")
            lines.append(f"Type: {type_name or category or 'Property'}")

            loc_parts = [x for x in [address, landmark, city, state] if x]
            if loc_parts:
                lines.append(f"Location: {', '.join(loc_parts)}")

            if total_area:
                lines.append(f"Area: {float(total_area):,.0f} {area_unit or 'sq ft'}")
            if bedrooms:
                bath_str = f", {bathrooms} bath" if bathrooms else ""
                lines.append(f"Configuration: {bedrooms} BHK{bath_str}")
            if total_floors:
                lines.append(f"Building: G+{total_floors}")
            if facing:
                lines.append(f"Facing: {facing.replace('_', '-').title()}")
            if road_width:
                lines.append(f"Road Width: {road_width}")
            if plot_dimensions:
                lines.append(f"Plot Dimensions: {plot_dimensions}")

            if price_on_request:
                if price_per_unit:
                    lines.append(f"Price: ₹{float(price_per_unit):,.0f} per {price_unit or 'sq ft'} — call for exact quote")
                else:
                    lines.append("Price: On request — call for pricing")
            else:
                if listed_price:
                    lines.append(f"Listed Price: ₹{float(listed_price):,.2f}")
                if discounted_price and listed_price and float(discounted_price) != float(listed_price):
                    lines.append(f"Discounted Price: ₹{float(discounted_price):,.2f}")
                if price_per_unit:
                    lines.append(f"Rate: ₹{float(price_per_unit):,.0f} per {price_unit or 'sq ft'}")
            if is_negotiable:
                lines.append("Negotiable: Yes")
            if booking_amount:
                lines.append(f"Booking Amount: ₹{float(booking_amount):,.0f}")

            if possession_status:
                lines.append(f"Possession: {possession_status.replace('_', ' ').title()}")
            if rera_number:
                lines.append(f"RERA: {rera_number}")

            if description:
                lines.append(f"About: {description.strip()[:500]}")

            amens = amenities_map.get(pid, [])
            if amens:
                lines.append(f"Amenities: {', '.join(amens)}")

            if contact_name:
                phone_str = f" — {contact_phone}" if contact_phone else ""
                lines.append(f"Site Contact: {contact_name}{phone_str}")

            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[LIVE-PROPS] Failed to fetch live properties: {e}")
        return ""


# Categories that get full per-product detail listing
_MARKET_DETAIL_CATS = {"BATTERY", "CHARGER", "MOTOR", "CONTROLLER", "BMS", "INVERTER"}

def _fetch_live_marketplace_knowledge(db: Session) -> str:
    """Query marketplace_spares live — grouped by category.
    High-value categories get per-product detail; others get a count + price range summary.
    Called on every call so any product add/edit/delete is instantly reflected."""
    try:
        rows = db.execute(text("""
            SELECT id, sku, name, category_name, brand,
                   dealer_price, gst_percent,
                   specifications, description,
                   model_compat, speciality,
                   warranty_details, color,
                   available_qty, stock_qty
            FROM marketplace_spares
            WHERE is_active = true
            ORDER BY category_name, dealer_price
        """)).fetchall()

        if not rows:
            return ""

        # Group by category
        cats: dict = _defaultdict(list)
        for r in rows:
            cats[r[3]].append(r)

        lines = [
            "### LIVE EV MARKETPLACE — Zynova EV Spares (VGK Real Dreams)",
            "These are the ACTUAL products currently in our catalogue. Prices are dealer prices (+ GST where applicable).\n",
        ]

        for cat_name in sorted(cats.keys()):
            products = cats[cat_name]
            prices = [float(p[5]) for p in products if p[5] and float(p[5]) > 0]
            in_stock = sum(1 for p in products if p[13] and p[13] > 0)
            avail_note = f"{in_stock} in stock" if in_stock > 0 else "check availability with team"

            if cat_name in _MARKET_DETAIL_CATS:
                # Full per-product listing
                lines.append(f"── {cat_name} ({len(products)} products, {avail_note}) ──")
                for p in products:
                    (pid, sku, name, cat, brand,
                     price, gst, specs, desc,
                     model_compat, speciality, warranty, color,
                     avail_qty, stock_qty) = p
                    parts = [f"  • {name}"]
                    if specs and specs.strip():
                        parts.append(f"[{specs.strip()}]")
                    if brand and brand.strip() and brand.strip().lower() not in ("common", ""):
                        parts.append(f"Brand: {brand.strip()}")
                    if price and float(price) > 0:
                        gst_str = f" +{int(float(gst))}% GST" if gst and float(gst) > 0 else ""
                        parts.append(f"₹{float(price):,.0f}{gst_str}")
                    if warranty and warranty.strip():
                        parts.append(f"Warranty: {warranty.strip()}")
                    if model_compat and model_compat.strip():
                        parts.append(f"Fits: {model_compat.strip()}")
                    lines.append("  " + "  |  ".join(parts[0:1]) + "  —  " + ",  ".join(parts[1:]) if len(parts) > 1 else parts[0])
                lines.append("")
            else:
                # Summary line only
                if prices:
                    price_str = f"₹{min(prices):,.0f}–₹{max(prices):,.0f}"
                else:
                    price_str = "price on request"
                lines.append(f"  • {cat_name}: {len(products)} products, {price_str} ({avail_note})")

        lines.append("")
        lines.append("NOTE: For products not listed above, tell the customer you can check and get back to them.")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[LIVE-MARKET] Failed to fetch marketplace products: {e}")
        return ""


def _build_system_prompt(
    db: Session, company_id: int, language: str,
    lead_name: str = "", segment: str = "", is_test: bool = False,
    agent_name: str = "Vidya"
) -> str:
    """Build GPT system prompt injecting product catalogue for this company.
    For test calls: optionally filter to a single segment.
    For LIVE calls: ALWAYS include General + Myntreal Hub segments plus the
    campaign segment so the agent knows about ALL products/brands the company offers."""
    params: dict = {"cid": company_id}
    if segment and is_test:
        # Test call — narrow focus to one segment only
        q = """
            SELECT segment, category, title, content
            FROM ai_product_catalogue
            WHERE company_id = :cid AND is_active = TRUE AND segment = :seg
            ORDER BY segment, category, sort_order
        """
        params["seg"] = segment
    else:
        # Live call — load ALL segments so Vidya can answer ANY question
        q = """
            SELECT segment, category, title, content
            FROM ai_product_catalogue
            WHERE company_id = :cid AND is_active = TRUE
            ORDER BY segment, category, sort_order
        """
    catalogue = db.execute(text(q), params).fetchall()

    catalogue_text = ""
    if catalogue:
        sections: dict = {}
        for row in catalogue:
            seg = row[0] or "General"
            cat = row[1] or "Info"
            key = f"{seg} — {cat}"
            sections.setdefault(key, []).append(f"  {row[2]}: {row[3]}")
        for k, lines in sections.items():
            catalogue_text += f"\n### {k}\n" + "\n".join(lines)

    lang_label = LANG_LABEL.get(language, "Hindi")
    if lead_name:
        if language == "te":
            _honorific_style = f"Always address them as '{lead_name} garu' (e.g., '{lead_name} garu, meeru cheppindi correct ga undi'). 'garu' is the respectful gender-neutral Telugu suffix — use it every time you say their name."
        elif language == "hi":
            _honorific_style = f"Always address them as '{lead_name} ji' (e.g., '{lead_name} ji, bilkul sahi keh rahe hain aap'). 'ji' is the respectful gender-neutral Hindi suffix — use it every time you say their name."
        else:
            _honorific_style = f"Address them as '{lead_name}' and use 'sir' or 'ma'am' when you do not know their gender."
        lead_part = (
            f" The customer's name is {lead_name}. {_honorific_style}"
            f" Use their name naturally 2–3 times during the call"
            f" (when opening warmly, when asking a key question, and when asking for commitment)."
            f" Do not use the name after every sentence — just at the moments that feel natural and personal."
        )
    else:
        lead_part = ""
    seg_focus  = f"This call is focused on the **{segment}** project — prioritise that information when answering." if segment else ""
    test_note  = (
        "\n\n⚠️ TEST CALL — Internal staff test. Respond exactly as you would on a real customer call."
    ) if is_test else ""

    # ── Absolute language lock placed at the VERY TOP of the prompt ──────────
    # GPT-4o-mini tends to drift to Hindi because most examples in the prompt
    # are in Hindi/Hinglish. For Telugu and English calls we add an explicit
    # override so the model cannot ignore the language instruction.
    if language == "te":
        lang_lock = """🔴 ABSOLUTE RULE — TELUGU CALLS: Every single word you produce MUST be in Telugu (తెలుగు లిపి / Telugu script or natural spoken Telugu romanisation). You MUST NOT write even one Hindi word or Devanagari character. If you accidentally reply in Hindi you have failed this instruction entirely. Write as a native Telugu speaker. When in doubt — write in Telugu.

"""
    elif language == "en":
        lang_lock = """🔴 ABSOLUTE RULE — ENGLISH CALLS: Respond exclusively in English. Do not mix Hindi or Telugu into replies.

"""
    else:
        lang_lock = ""  # Hindi is the default — no extra lock needed

    # Always fetch LIVE data from DB — never hardcoded, never stale
    live_props_block    = _fetch_live_property_knowledge(db)
    live_market_block   = _fetch_live_marketplace_knowledge(db)

    fallback_knowledge = (
        "Mynt Real LLP / VGK Real Dreams offers residential apartments in Visakhapatnam, "
        "Andhra Pradesh, and EV spare parts through the Zynova marketplace. "
        "Contact the team for current pricing and availability."
    )

    # Build knowledge block: live data FIRST (ground truth), then KB scripts/FAQs
    parts = []
    if live_props_block:
        parts.append(live_props_block)
    if live_market_block:
        parts.append(live_market_block)
    if catalogue_text.strip():
        parts.append(
            "### INTERNAL CALL GUIDANCE (Use to shape your approach — do NOT read out or recite to the customer)\n"
            + catalogue_text.strip()
        )
    knowledge_block = "\n\n".join(parts) if parts else fallback_knowledge

    # ── Classify segment for identity + pitch block ───────────────────────────
    _kind      = _segment_kind(segment)
    _seg_lower = (segment or "").lower()
    _cat_lower = catalogue_text.lower()
    if _kind == "solar" or "solar" in _cat_lower:
        solar_pitch_block = f"""
━━━ SOLAR ENERGY PITCH GUIDE ━━━
When speaking with a Solar lead, ALWAYS probe for electricity consumption first — then calculate and pitch savings.

STEP 1 — PROBE (pick the right language):
- {"Telugu: 'Meeru oka nela lo entha electricity vadataro — units lo cheppagalara? Ya meeru monthly bill enta vastundi?'" if language == "te" else "English: 'How many units of electricity do you use monthly? Or what's your approximate monthly bill?'" if language == "en" else "Hindi: 'Aap ek mahine mein kitni electricity use karte hain — units mein bata sakte hain? Ya monthly bill kitna aata hai?'"}

STEP 2 — CALCULATE APPROXIMATE BILL (if they give UNITS):
Use this range (Indian electricity tariff slabs):
  ≤100 units/month  →  ₹500–₹900/month
  101–200 units     →  ₹900–₹1,800/month
  201–300 units     →  ₹1,800–₹3,500/month
  301–500 units     →  ₹3,500–₹6,000/month
  500+ units        →  ₹6,000–₹12,000+/month (commercial slabs kick in)
{"Say the range naturally: 'XXX units ki meeru bill daadaapu ₹Y nundi ₹Z varaku untundi.'" if language == "te" else "Say the range naturally: 'For XXX units your bill would be approximately ₹Y to ₹Z per month.'" if language == "en" else "Say the range naturally: 'XXX units pe aapka bill approximately ₹Y se ₹Z tak aata hoga.'"}

STEP 3 — PITCH SOLAR SAVINGS:
{"Telugu: 'Solar panel pettukunte ee bill 80–90% thaggipotundi. PM Surya Ghar scheme lo ₹78,000 varaku subsidy kuda milutundi. Saadhaarananga 3–4 sallallo cost recover avutundi — atapaiki 20 sallalu almost free electricity!'" if language == "te" else "English: 'With solar, this bill can drop by 80–90%. Under the PM Surya Ghar scheme you get up to ₹78,000 subsidy. Most customers recover the cost in 3–4 years — after that it is nearly free electricity for 20+ years!'" if language == "en" else "Hindi: 'Solar lagao to yeh bill 80–90% kam ho jaata hai. PM Surya Ghar scheme mein ₹78,000 tak subsidy milti hai. 3–4 saal mein cost recover ho jaata hai — uske baad 20 saal free electricity!'"}

THEN ASK: {"'Aapka ghar ka area kitna hai — aur roof pe jagah hai? Main aapke liye sahi system size suggest kar sakta/sakti hoon.'" if language == "hi" else "'Meeru intlo challa roof space undha? Mee ki sari ayna system size suggest cheyagalanu.'" if language == "te" else "'What is your home or business area, and do you have rooftop space? I can suggest the right system size.'"}

IMPORTANT: Only pitch solar savings after you know their consumption. Never pitch without probing first.
"""
    else:
        solar_pitch_block = ""

    # Gender-aware language fragments (Hindi) based on agent name
    _is_male = agent_name.lower() in ("karthik", "arjun", "rahul", "ravi")
    _g_raha   = "raha" if _is_male else "rahi"
    _g_sakta  = "sakta" if _is_male else "sakti"
    _g_batata = "batata" if _is_male else "batati"
    _g_samajh = "chahta" if _is_male else "chahti"
    _g_nikal  = "nikalta" if _is_male else "nikaalti"

    # Language-specific "don't know" fallback phrase
    _dont_know_phrase = (
        "Ee vishayam naaku ippudu teliyadhu, confirm chesi chepthaanu."
        if language == "te" else
        "I don't have that detail right now — I'll confirm and get back to you."
        if language == "en" else
        f"Ye detail abhi mere paas nahi hai, main confirm karke {_g_batata} hoon."
    )

    # Language-specific probing phrases
    if language == "te":
        _probing_phrases = """Human probing phrases to use naturally (in Telugu):
- "Okka nimisham — mundu cheppandi..."
- "Naaku artham chesukovandam — exact ga em problem vastundi?"
- "Budget ki anuguna ga best option suggest cheyagalanu\""""
    elif language == "en":
        _probing_phrases = """Human probing phrases to use naturally:
- "Just a moment — first tell me..."
- "I want to understand — what exactly is the issue you're facing?"
- "Based on your budget, I can suggest the best option\""""
    else:
        _probing_phrases = f"""Human probing phrases to use naturally:
- "Ek second — pehle yeh batao ki..."
- "Main samajhna {_g_samajh} hoon — exactly kya problem aa rahi hai?"
- "Budget ke hisaab se main sahi option suggest kar {_g_sakta} hoon\""""

    _seg_intro = _segment_agent_intro(_kind, agent_name, language)
    _seg_scope = {
        "solar": "You are a solar specialist — focus entirely on helping the customer understand solar rooftop benefits, the PM Surya Ghar government subsidy, and the installation process.",
        "ev":    "You are an EV parts specialist — focus on helping the customer identify the right EV battery, charger, motor or spare part for their vehicle. You also handle property enquiries if asked.",
        "hub":   "You are a property specialist for the Myntreal Hub project — focus on project details, pricing, RERA, amenities and payment plans. You can also assist with other VGK properties.",
    }.get(_kind, "You handle residential properties listed on VGK Real Dreams AND EV spare parts on the Zynova marketplace — answer whatever the customer asks about.")

    # ── Pre-compute "not interested" persuasion blocks (avoid nested f-string issues) ──
    if language == "te":
        _ni_ask_2min = (
            "Okay sir/madam — okka rendu nimishalu ivvagalara? "
            "Meeru oka important vishayam cheppali anukuntunnanu — "
            "cheppite definitely mee ki use avutundi ani anipistundi."
        )
        _ni_close = (
            "Sare sir/madam — mee time ki chala thanks. "
            "Mee ki oka maanchi roju avugaak. "
            "Inka em avasaramaina contact cheyaandi — happy to help!"
        )
    elif language == "en":
        _ni_ask_2min = (
            "I completely understand — but could you spare just 2 minutes? "
            "There is one thing I genuinely believe will be useful for you "
            "and I would not want you to miss it."
        )
        _ni_close = (
            "Absolutely, I completely respect that. "
            "Thank you so much for your time — have a wonderful day! "
            "Do reach out if you ever need us."
        )
    else:
        _ni_ask_2min = (
            f"Main samajh {_g_raha} hoon — lekin kya aap bas 2 minute de sakte hain? "
            f"Ek cheez share karna {_g_samajh} hoon jo sach mein aapke liye kaam ki hai, "
            "miss nahi karna chahiye."
        )
        _ni_close = (
            "Bilkul, aapka time dene ke liye bahut shukriya. "
            "Aapka din shubh ho! Kabhi bhi zaroorat ho toh zaroor contact karein."
        )

    if _kind == "solar":
        if language == "te":
            _ni_segment_pitch = (
                "VGK Real Dreams oka trusted solar company — 500+ installations tho. "
                "Mee ki important ga cheppali: PM Surya Ghar Yojana scheme lo government direct ga "
                "78,000 rupayalu subsidy istundi — idi government money, meeru pocket lo padadhu. "
                "Plus meeru electricity bill 80 to 90 percent thaggipotundi. "
                "Oka 5kW system ki total cost daadaapu 2.5 nundi 3 lakh varaku untundi — "
                "subsidy poyaka net cost sirf 1.5 nundi 2 lakh matrame. "
                "3 to 4 sallallo ee cost recover avutundi — atapaiki 20 sallalu almost free electricity! "
                "Idi oka sari alochinchukovalasina chance."
            )
        elif language == "en":
            _ni_segment_pitch = (
                "VGK Real Dreams is a trusted solar company with 500+ successful installations. "
                "Here is what I want you to know: under the PM Surya Ghar Yojana, "
                "the government directly gives you up to Rs 78,000 subsidy — real government money. "
                "Your electricity bill drops by 80 to 90 percent. "
                "A 5kW system costs around Rs 2.5 to 3 lakh total — after subsidy your net cost is just Rs 1.5 to 2 lakh. "
                "You recover that in 3 to 4 years. After that — nearly free electricity for 20 or more years. "
                "This is genuinely worth 2 minutes."
            )
        else:
            _ni_segment_pitch = (
                "VGK Real Dreams ek trusted solar company hai — 500 se zyada successful installations ke saath. "
                "Ek important baat: PM Surya Ghar Yojana ke through government seedha 78,000 rupaye subsidy deti hai — "
                "yeh government ka paisa hai, aapki jeb mein aata hai. "
                "Bijli bill 80 se 90 percent kam ho jaata hai. "
                "Ek 5kW system ka total kharcha Rs 2.5 se 3 lakh hai — subsidy ke baad net cost sirf Rs 1.5 se 2 lakh. "
                "3 se 4 saal mein recover ho jaata hai — uske baad 20 saal almost free electricity!"
            )
    elif _kind in ("hub", "property"):
        if language == "te":
            _ni_segment_pitch = (
                "VGK Real Dreams — Vizag lo 15 plus sallala experience tho. "
                "Myntreal Hub RERA registered project — government approved, mee money completely safe. "
                "Prime location, world-class amenities, pre-launch pricing. "
                "Real estate lo idi oka rare opportunity — "
                "oka chinna visit chesthe meeru self ga feel avutaaru."
            )
        elif language == "en":
            _ni_segment_pitch = (
                "VGK Real Dreams has 15 plus years of experience in Visakhapatnam. "
                "Myntreal Hub is a RERA-registered project — government approved, your money is completely protected. "
                "Prime location, world-class amenities, pre-launch pricing that locks in future appreciation. "
                "This is a rare opportunity in Vizag real estate. "
                "Just a quick site visit and you will feel the difference yourself."
            )
        else:
            _ni_segment_pitch = (
                "VGK Real Dreams ka Visakhapatnam mein 15 saal se zyada ka experience hai. "
                "Myntreal Hub ek RERA registered project hai — government approved, aapka paisa completely safe. "
                "Prime location, world-class amenities, pre-launch pricing. "
                "Real estate mein yeh ek rare chance hai — bas ek choti si site visit aur aap khud feel karenge."
            )
    elif _kind == "ev":
        if language == "te":
            _ni_segment_pitch = (
                "Zynova marketplace — OEM kante 30 to 40 percent thaggaga same quality EV parts, warranty tho saha. "
                "Certified products, fast delivery. "
                "Oka sari price compare chesthe meeru cheppindi artham avutundi."
            )
        elif language == "en":
            _ni_segment_pitch = (
                "Zynova marketplace offers the same quality EV parts at 30 to 40 percent less than OEM prices — "
                "with full warranty and certified quality. Fast delivery, genuine parts. "
                "One price comparison and you will understand what I mean."
            )
        else:
            _ni_segment_pitch = (
                "Zynova marketplace par OEM se 30 se 40 percent kam mein same quality EV parts milte hain — "
                "warranty ke saath. Certified products, fast delivery. "
                "Ek baar price compare karo aur aap khud samjh jaoge."
            )
    else:
        _ni_segment_pitch = (
            "VGK Real Dreams is a trusted real estate and solar company in Visakhapatnam with 15 plus years of experience. "
            "Our projects are RERA registered, government approved, and backed by a strong track record. "
            "Whether it is property investment or solar savings — this is worth 2 minutes of your time."
        )

    return f"""{lang_lock}You are {agent_name}; {_seg_intro}{lead_part}
{_seg_scope}
You are on a live phone call. Sound like a real person — warm, natural, knowledgeable. Never like a bot or a script.

━━━ YOUR VOICE & ACCENT ━━━
You have a natural Telugu mother tongue influence in your speech:
- In Hindi: soft, slightly musical South Indian cadence — "v" sounds gentle, vowels slightly warm and elongated. You naturally say "kaabatti", "anthe", "choodandi", "ayithe" even in Hindi conversation. Your Hindi has the warmth of a Telugu speaker — never flat or Northern.
- In Telugu: speak as a natural native speaker — fluent, comfortable, using everyday expressions like "okay aa", "cheppandi", "undi", "antaaru", "kaadhu".
- In English: gentle South Indian warmth — measured, clear, friendly. Never flat or robotic.
This accent is your identity — it makes you sound real, trustworthy, and relatable. Never suppress it.
{seg_focus}

━━━ #1 PRIORITY: ANSWER THE CUSTOMER'S QUESTION ━━━
When a customer asks ANYTHING — answer it DIRECTLY from your knowledge base.

PROPERTY QUESTIONS:
• Price? → exact price / rate per sq ft from the listing
• Location? → address, landmark, city, distance
• Amenities? → list them from the property
• Possession? → Ready / Under Construction + timeline
• RERA? → number if available
• Payment? → booking amount, loan assistance

EV SPARE PARTS QUESTIONS:
• Battery / charger / motor asked → quote the actual specs and price from your knowledge
• Availability → all stock is subject to confirmation with the team
• Warranty → mention if listed

NEVER say "our team will share details" when you know the answer.
NEVER skip answering to jump to sales tactics.
Answer first. Fully. Then naturally continue the conversation.

If you genuinely don't know → "{_dont_know_phrase}"

━━━ YOUR COMPLETE LIVE KNOWLEDGE BASE ━━━
{knowledge_block}

This data is pulled LIVE from the database every call. It is always current.
Treat it as your personal expertise — speak from it naturally, not like you're reading a list.
{solar_pitch_block}
━━━ MARKETPLACE PROBING — HOW TO HANDLE EV PARTS ENQUIRIES ━━━
When a customer asks about batteries, chargers, motors, or any EV spare:

PROBE first to understand their need — don't just quote prices:
1. "Aapka vehicle kaunsa hai — konsa model?" (which EV model?) / "Mee vehicle enti?" (Telugu)
2. "Abhi jo battery hai uski capacity kya hai?" (Hindi) / "Ippudu battery specs em unnai?" (Telugu)
3. "Koi specific problem aa rahi hai ya upgrade chahiye?" (Hindi) / "Em problem vastundi?" (Telugu)
4. "Kitna budget socha hai aapne?" (Hindi) / "Budget entha anukuntunnaru?" (Telugu)

Then match the RIGHT product from your knowledge base.

Example flow (Hindi):
Customer: "Battery chahiye"
{agent_name}: "Zaroor! Aapka kaunsa vehicle hai aur current battery ki voltage kya hai?"
[After answer] → "Okay, aapke liye LFP 48V 30AH best rahega — dealer price ₹20,433 hai, 2+1 saal ki warranty ke saath. Kya yeh range theek lagti hai?"

Example flow (Telugu):
Customer: "Battery kavali"
{agent_name}: "Cheppandi — mee vehicle enti, ippudu battery specs em unnai?"
[After answer] → "Mee ki LFP 52V 30AH baguntundi — price ₹21,057, warranty 2+1 years. Interest ga undaa?"

{_probing_phrases}

━━━ LANGUAGE ━━━
⚠️ PRIMARY LANGUAGE: {lang_label}. You MUST respond in {lang_label} unless the customer explicitly switches to a different language.
Do NOT default to English. Do NOT mix languages unless the customer does first.

- Hindi: Natural spoken Hindi — "haan ji", "bilkul", "acha", "dekhiye", "samajh gaya" — NOT formal written Hindi.
- Telugu: Natural spoken Telugu — "undi", "cheppandi", "ayithe", "okay aa", "choodandi".
- English: Warm, conversational. Like talking to a trusted advisor, not a salesperson.

If a customer speaks in a different language than {lang_label}, mirror them and continue in their language for that turn — then gently confirm: "Shall I continue in [new language]?"
Never mix scripts mid-sentence. Match the customer's register.
⚠️ ALL EXAMPLE PHRASES BELOW ARE IN HINDI FOR REFERENCE ONLY. You MUST say these equivalents in {lang_label} on this call.
INTERNAL GUIDANCE NOTE: The "INTERNAL CALL GUIDANCE" section above contains scripts and strategy notes to help you understand what to focus on and how to handle objections. Do NOT read these notes out loud or treat them as things to say to the customer — use them as background knowledge to inform your natural conversation.

━━━ CONVERSATION MOMENTUM RULES ━━━
After answering, ALWAYS move the conversation FORWARD. Never leave it hanging.
IMPORTANT: Express these in {lang_label} — NOT Hindi (unless this is a Hindi call).

WHEN CUSTOMER CONFIRMS INTEREST / SAYS YES / "READY" / "OKAY":
→ Immediately close for a concrete next step. Do NOT ask another open question.
→ Property (Hindi ref): "Toh ek site visit fix karte hain — aap is weekend free hain ya weekday better hai?"
→ Property (Telugu): "Alaaantey oka site visit fix cheydam — ee weekend free ga unnaraa leka weekday better aa?"
→ Parts (Hindi ref): "Main abhi order raise kar sakta/sakti hoon — aapka delivery address confirm karein?"
→ Parts (Telugu): "Naenu ippude order raise cheyagalanu — mee delivery address confirm cheyagalara?"

WHEN CUSTOMER ASKS FOR MORE DETAILS:
→ Give the 2-3 most important facts DIRECTLY (price, timeline, ROI, what's included).
→ Hindi ref: "Is mein se koi ek cheez aur clear karni hai?"
→ Telugu ref: "Ee vishayaallo oka vishayam inka clear chesukovalaa?"

OBJECTION HANDLING (express these IN {lang_label}):
→ "Thinking" → Encourage a site visit first — seeing is believing
→ "Budget tight" (property) → Finance & home loan assistance available; EMI makes it feasible
→ "Budget tight" (parts) → Ask exact budget; find the best fit within their range
→ "Already have property" → Investment/rental income angle for second property
→ "Busy" → Ask best time to call back, [CALLBACK]

HANDLING "NOT INTERESTED" / "NO" -- MANDATORY TWO-STEP PERSUASION
RULE: NEVER accept the FIRST "no". You MUST make one genuine convincing attempt.
RULE: Only [END_CALL] after a SECOND clear refusal.

--- STEP 1: FIRST REJECTION --- Ask for 2 minutes then pitch company highlights ---
When the customer says "not interested", "no", "vaddhu", "nahi chahiye", or similar:

FIRST -- Acknowledge warmly and ask for exactly 2 minutes:
"{_ni_ask_2min}"

THEN -- Immediately share this pitch about the company and their specific product:
"{_ni_segment_pitch}"

--- STEP 2: SECOND REJECTION --- Respect and close warmly ---
Only after a SECOND clear "not interested" do you end the call gracefully:
"{_ni_close}"
[END_CALL]

TRACK "not interested" count in the conversation history. [END_CALL] ONLY on count >= 2.

⛔ NEVER END A RESPONSE WITH PASSIVE PHRASES LIKE:
- "...naku cheppandi" / "...ikkadey unnanu" / "...ready ga unnanu"
- "...miku help cheyadaniki ikkadey unnanu"
- "If you have any questions, I'm here"
- "Feel free to ask"
→ These waste the customer's time and kill momentum. Every reply must move toward a meeting, a visit, or an order.

━━━ PHONE CALL FORMAT RULES ━━━
⚠️ CRITICAL — THIS IS A LIVE PHONE CALL. The customer is waiting on the line.
- MAX 3 sentences per turn. Give ONE complete answer, then ask ONE targeted question.
- Never list bullet points. Weave facts into natural spoken sentences.
- If they ask "tell me everything" — give the 2 most important facts, then anchor with one question.
- Short, direct answers feel confident. Rambling feels like a bot reading a brochure.
- Never sound like you're reading. Use natural spoken rhythm.
- NEVER re-introduce yourself after the first turn — "Nenu Vidya ni / I am Vidya" only once, in the greeting.
- [END_CALL] or [CALLBACK] — use ONLY at the very end of a message, only after minimum 3 turns.
- Never reveal you are an AI, a bot, or using any system{test_note}"""


def _clean_old_audio():
    """Remove audio files older than 2 hours."""
    try:
        cutoff = get_ist_now().timestamp() - 7200
        for fn in os.listdir(AI_AUDIO_DIR):
            fp = os.path.join(AI_AUDIO_DIR, fn)
            if os.path.getmtime(fp) < cutoff:
                os.remove(fp)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# PRODUCT CATALOGUE CRUD
# ─────────────────────────────────────────────────────────

@router.get("/catalogue")
def get_catalogue(
    segment: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    query = """
        SELECT id, company_id, segment, category, title, content, is_active, sort_order,
               created_by, created_at, updated_at
        FROM ai_product_catalogue
        WHERE company_id = :cid
    """
    params: dict = {"cid": current_user.base_company_id}
    if segment:
        query += " AND segment = :seg"
        params["seg"] = segment
    if category:
        query += " AND category = :cat"
        params["cat"] = category
    query += " ORDER BY segment, category, sort_order, id"
    rows = db.execute(text(query), params).fetchall()
    return {"success": True, "items": [
        {"id": r[0], "company_id": r[1], "segment": r[2], "category": r[3],
         "title": r[4], "content": r[5], "is_active": r[6], "sort_order": r[7],
         "created_by": r[8],
         "created_at": r[9].isoformat() if r[9] else None,
         "updated_at": r[10].isoformat() if r[10] else None}
        for r in rows
    ]}


@router.get("/catalogue/segments")
def get_catalogue_segments(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    rows = db.execute(text("""
        SELECT DISTINCT segment FROM ai_product_catalogue
        WHERE company_id = :cid AND is_active = TRUE ORDER BY segment
    """), {"cid": current_user.base_company_id}).fetchall()
    categories = db.execute(text("""
        SELECT DISTINCT category FROM ai_product_catalogue
        WHERE company_id = :cid ORDER BY category
    """), {"cid": current_user.base_company_id}).fetchall()
    return {
        "success": True,
        "segments": [r[0] for r in rows if r[0]],
        "categories": [r[0] for r in categories if r[0]],
    }


@router.post("/catalogue")
def create_catalogue_entry(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    segment  = (payload.get("segment") or "").strip()
    category = (payload.get("category") or "").strip()
    title    = (payload.get("title") or "").strip()
    content  = (payload.get("content") or "").strip()
    if not segment or not title or not content:
        raise HTTPException(status_code=400, detail="segment, title, and content are required")
    sort_order = int(payload.get("sort_order", 0))
    # Auto-elaborate brief content so Vidya has richer answers
    original_content = content
    elaborated_content = _elaborate_content(content, title, segment)
    result = db.execute(text("""
        INSERT INTO ai_product_catalogue
            (company_id, segment, category, title, content, sort_order, created_by, is_active)
        VALUES (:cid, :seg, :cat, :title, :content, :order, :creator, TRUE)
        RETURNING id
    """), {
        "cid": current_user.base_company_id, "seg": segment, "cat": category,
        "title": title, "content": elaborated_content, "order": sort_order,
        "creator": current_user.emp_code,
    })
    db.commit()
    new_id = result.fetchone()[0]
    # Trigger gap analysis in background
    import threading
    threading.Thread(
        target=_run_gap_analysis_bg,
        args=(current_user.base_company_id, segment, title, elaborated_content),
        daemon=True,
    ).start()
    return {
        "success": True, "id": new_id, "message": "Catalogue entry created",
        "elaborated": elaborated_content != original_content,
        "content_saved": elaborated_content,
    }


@router.put("/catalogue/{entry_id}")
def update_catalogue_entry(
    entry_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id FROM ai_product_catalogue WHERE id=:id AND company_id=:cid"
    ), {"id": entry_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    fields, params = [], {"id": entry_id, "cid": current_user.base_company_id}
    for col in ("segment", "category", "title", "content", "sort_order", "is_active"):
        if col in payload:
            fields.append(f"{col} = :{col}")
            params[col] = payload[col]
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    fields.append("updated_at = NOW()")
    db.execute(text(
        f"UPDATE ai_product_catalogue SET {', '.join(fields)} WHERE id=:id AND company_id=:cid"
    ), params)
    db.commit()
    return {"success": True, "message": "Entry updated"}


@router.delete("/catalogue/{entry_id}")
def delete_catalogue_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id FROM ai_product_catalogue WHERE id=:id AND company_id=:cid"
    ), {"id": entry_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.execute(text(
        "DELETE FROM ai_product_catalogue WHERE id=:id AND company_id=:cid"
    ), {"id": entry_id, "cid": current_user.base_company_id})
    db.commit()
    return {"success": True, "message": "Entry deleted"}


# ─────────────────────────────────────────────────────────
# KNOWLEDGE GAP ANALYSIS
# ─────────────────────────────────────────────────────────

def _elaborate_content(content: str, title: str, segment: str) -> str:
    """GPT-expand a brief KB entry into a natural, conversational answer for Vidya."""
    if len(content) >= 150 or not OPENAI_KEY:
        return content
    import httpx as _hx
    prompt = f"""You are a real estate knowledge base editor.
Expand this brief entry into 2-3 detailed, natural sentences that a sales AI can use in a phone call.
Include specific benefits and customer-focused language. Write in Hinglish (Hindi + English mix).

Segment: {segment}
Title: {title}
Brief: {content}

Return ONLY the expanded content. No labels, no JSON, no markdown."""
    try:
        r = _hx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 200, "temperature": 0.4},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip() or content
    except Exception:
        return content


def _run_gap_analysis_bg(company_id: int, segment: str, entry_title: str, entry_content: str):
    """Background: run GPT gap analysis for a catalogue entry and save missing questions."""
    if not OPENAI_KEY:
        return
    import httpx as _hx
    prompt = f"""You are reviewing a real estate knowledge base entry. Identify 3-5 specific questions a customer might ask during a sales call that CANNOT be answered from this entry alone.

Segment: {segment}
Title: {entry_title}
Content: {entry_content}

Return a JSON array of objects with:
- "question": the customer question in English
- "suggested_answers": array of 3 short possible answers (strings, in Hinglish) the admin can choose from

Return ONLY valid JSON array. No explanation."""
    try:
        r = _hx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 600, "temperature": 0.3},
            timeout=30,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        gaps = json.loads(raw.strip())
        if not isinstance(gaps, list):
            gaps = [gaps]
        db = _SessionLocal()
        try:
            for g in gaps:
                db.execute(text("""
                    INSERT INTO ai_catalogue_gaps (company_id, segment, question, suggested_answers)
                    VALUES (:cid, :seg, :q, CAST(:sa AS jsonb))
                """), {
                    "cid": company_id, "seg": segment,
                    "q": g.get("question", ""),
                    "sa": json.dumps(g.get("suggested_answers", [])),
                })
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[GAP_ANALYSIS] failed: {e}")


_KNOWN_CATEGORIES = [
    "Project Details", "Pricing", "Location", "Amenities",
    "Payment Plan", "RERA & Legal", "USPs", "Contact", "FAQs",
]


def _ai_enrich_and_save(
    company_id: int,
    raw_input: str,
    question: str,
    creator: str,
    db,
    context_segment: str = "",
) -> list:
    """
    Use GPT-4o-mini to:
      1. Understand raw text/voice input about a real estate property
      2. Determine which segment(s) and category(ies) it belongs to
      3. Elaborate into complete, natural KB content
      4. Save one or more entries to ai_product_catalogue
    Returns list of saved entry dicts {id, segment, category, title, content}.
    """
    if not OPENAI_KEY:
        return []

    # Fetch existing segments so GPT can map to them
    seg_rows = db.execute(text("""
        SELECT DISTINCT segment FROM ai_product_catalogue
        WHERE company_id = :cid AND is_active = TRUE ORDER BY segment
    """), {"cid": company_id}).fetchall()
    existing_segs = [r[0] for r in seg_rows if r[0]] or ["General"]

    import httpx as _hx

    q_clause = f"\nCustomer Question that triggered this: {question}" if question else ""
    seg_hint  = f"\nPreferred Segment (if applicable): {context_segment}" if context_segment else ""

    prompt = f"""You are a knowledge-base editor for an AI phone sales agent (Mynt Real LLP / VGK Real Dreams).

A staff member provided the following raw information:
\"\"\"{raw_input}\"\"\"
{q_clause}
{seg_hint}

Existing KB segments: {', '.join(existing_segs)}
Valid categories: {', '.join(_KNOWN_CATEGORIES)}

Your task:
1. Read the ENTIRE input carefully — it may have multiple logical sections.
2. Create ONE knowledge base entry per logical section/topic (e.g. product info, pricing, highlights, sales instructions, FAQs — each gets its own entry).
3. Decide which segment each entry belongs to — use an existing segment or infer from context; use "General" only if truly universal.
4. For sales instructions / call strategy content: preserve the instructions verbatim or near-verbatim as the content — do NOT paraphrase into 3 sentences. The AI agent must follow these exactly.
5. For product/pricing/benefit info: rewrite as clear, natural Hinglish (Hindi+English) sentences the AI agent can speak naturally on calls.
6. Title: max 80 chars, descriptive.

Return a JSON array — one element per logical section. Each element:
{{
  "segment": "<segment name>",
  "category": "<one of: {', '.join(_KNOWN_CATEGORIES)}>",
  "title": "<concise title>",
  "content": "<content for this section>"
}}

Return ONLY the JSON array. No markdown fences, no explanation."""

    try:
        r = _hx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3000,
                "temperature": 0.3,
            },
            timeout=60,
        )
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
            if raw.endswith("```"):
                raw = raw[:-3]
        entries = json.loads(raw.strip())
        if isinstance(entries, dict):
            entries = [entries]
    except Exception as e:
        logger.warning(f"[AI_ENRICH] GPT parse failed: {e}")
        # Fallback: save raw as-is under context_segment or General
        fallback_seg = context_segment or "General"
        fallback_title = (question or raw_input)[:80]
        entries = [{"segment": fallback_seg, "category": "FAQs",
                    "title": fallback_title, "content": raw_input}]

    saved = []
    for entry in entries:
        seg  = (entry.get("segment") or context_segment or "General").strip()
        cat  = (entry.get("category") or "FAQs").strip()
        title   = (entry.get("title") or (question or raw_input)[:80]).strip()
        content = (entry.get("content") or raw_input).strip()
        try:
            res = db.execute(text("""
                INSERT INTO ai_product_catalogue
                    (company_id, segment, category, title, content, sort_order, created_by, is_active)
                VALUES (:cid, :seg, :cat, :title, :content, 900, :by, TRUE)
                RETURNING id
            """), {"cid": company_id, "seg": seg, "cat": cat,
                   "title": title, "content": content, "by": creator})
            new_id = res.fetchone()[0]
            saved.append({"id": new_id, "segment": seg, "category": cat,
                          "title": title, "content": content})
        except Exception as e:
            logger.warning(f"[AI_ENRICH] DB insert failed: {e}")
    if saved:
        db.commit()
    return saved


@router.post("/catalogue/ai-enrich")
def ai_enrich_kb(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """AI-powered KB enrichment: elaborate raw text/voice input and save to applicable segments."""
    raw_input = (payload.get("raw_input") or "").strip()
    question  = (payload.get("question") or "").strip()
    context_segment = (payload.get("context_segment") or "").strip()
    if not raw_input:
        raise HTTPException(status_code=400, detail="raw_input required")
    entries = _ai_enrich_and_save(
        company_id=current_user.base_company_id,
        raw_input=raw_input,
        question=question,
        creator=current_user.emp_code,
        db=db,
        context_segment=context_segment,
    )
    if not entries:
        raise HTTPException(status_code=500, detail="AI enrichment failed — check OpenAI key")
    return {"success": True, "entries_saved": len(entries), "entries": entries}


@router.post("/catalogue/elaborate")
def elaborate_catalogue_content(
    payload: dict = Body(...),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """GPT-elaborate a short KB entry. Returns original + elaborated version."""
    content  = (payload.get("content") or "").strip()
    title    = (payload.get("title") or "").strip()
    segment  = (payload.get("segment") or "General").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    elaborated = _elaborate_content(content, title, segment)
    return {"success": True, "original": content, "elaborated": elaborated,
            "expanded": len(elaborated) > len(content)}


@router.post("/catalogue/analyze-gaps")
def analyze_catalogue_gaps(
    payload: dict = Body(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Trigger GPT gap analysis for a catalogue entry — async, results appear in /catalogue/gaps."""
    segment = (payload.get("segment") or "General").strip()
    title   = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    if background_tasks:
        background_tasks.add_task(
            _run_gap_analysis_bg, current_user.base_company_id, segment, title, content
        )
    else:
        import threading
        threading.Thread(
            target=_run_gap_analysis_bg,
            args=(current_user.base_company_id, segment, title, content),
            daemon=True,
        ).start()
    return {"success": True, "message": "Gap analysis started. Results appear in Knowledge Gaps shortly."}


@router.get("/catalogue/gaps")
def list_catalogue_gaps(
    segment: str = Query(""),
    status: str = Query("pending"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """List all knowledge gap questions for this company."""
    cid = current_user.base_company_id
    where = "company_id=:cid"
    params: dict = {"cid": cid}
    if segment:
        where += " AND segment=:seg"
        params["seg"] = segment
    if status and status != "all":
        where += " AND status=:st"
        params["st"] = status
    rows = db.execute(text(f"""
        SELECT id, segment, question, suggested_answers, chosen_answer, status, created_at, answered_at
        FROM ai_catalogue_gaps WHERE {where}
        ORDER BY created_at DESC LIMIT 100
    """), params).fetchall()
    return {"success": True, "gaps": [
        {"id": r[0], "segment": r[1], "question": r[2],
         "suggested_answers": r[3] if r[3] else [],
         "chosen_answer": r[4], "status": r[5],
         "created_at": r[6].isoformat() if r[6] else None,
         "answered_at": r[7].isoformat() if r[7] else None}
        for r in rows
    ]}


@router.post("/catalogue/gaps/{gap_id}/answer")
def answer_catalogue_gap(
    gap_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Save an answer to a gap question and optionally save it to the knowledge base."""
    cid    = current_user.base_company_id
    answer = (payload.get("answer") or "").strip()
    save   = payload.get("save_to_kb", False)
    if not answer:
        raise HTTPException(status_code=400, detail="answer required")
    row = db.execute(text(
        "SELECT segment, question FROM ai_catalogue_gaps WHERE id=:id AND company_id=:cid"
    ), {"id": gap_id, "cid": cid}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Gap not found")
    segment, question = row[0], row[1]
    db.execute(text("""
        UPDATE ai_catalogue_gaps
        SET chosen_answer=:ans, status='answered', answered_at=NOW()
        WHERE id=:id AND company_id=:cid
    """), {"ans": answer, "id": gap_id, "cid": cid})
    db.commit()
    saved_entries = []
    if save:
        saved_entries = _ai_enrich_and_save(
            company_id=cid,
            raw_input=answer,
            question=question,
            creator=current_user.emp_code,
            db=db,
            context_segment=segment or "General",
        )
    return {"success": True, "saved_to_kb": save, "entries_saved": saved_entries}


# ─────────────────────────────────────────────────────────
# UNANSWERED QUESTIONS (from live calls)
# ─────────────────────────────────────────────────────────

@router.get("/unanswered-questions")
def list_unanswered_questions(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """List all questions Vidya could not answer during calls."""
    cid = current_user.base_company_id
    rows = db.execute(text("""
        SELECT uq.id, uq.log_id, uq.question, uq.ai_reply, uq.answer,
               uq.answered_by, uq.answered_at, uq.saved_to_kb, uq.created_at,
               cl.name, cl.phone,
               acl.campaign_id
        FROM ai_unanswered_questions uq
        JOIN ai_call_logs acl ON acl.id = uq.log_id
        LEFT JOIN crm_leads cl ON cl.id = acl.lead_id
        WHERE uq.company_id = :cid
        ORDER BY uq.created_at DESC
        LIMIT 200
    """), {"cid": cid}).fetchall()
    return {"success": True, "questions": [
        {"id": r[0], "log_id": r[1], "question": r[2], "ai_reply": r[3],
         "answer": r[4], "answered_by": r[5],
         "answered_at": r[6].isoformat() if r[6] else None,
         "saved_to_kb": r[7],
         "created_at": r[8].isoformat() if r[8] else None,
         "lead_name": r[9], "lead_phone": r[10], "campaign_id": r[11]}
        for r in rows
    ]}


@router.post("/unanswered-questions/{uq_id}/answer")
def answer_unanswered_question(
    uq_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Save an answer to an unanswered call question and optionally add to KB."""
    cid    = current_user.base_company_id
    answer = (payload.get("answer") or "").strip()
    save   = payload.get("save_to_kb", False)
    if not answer:
        raise HTTPException(status_code=400, detail="answer required")
    row = db.execute(text(
        "SELECT question FROM ai_unanswered_questions WHERE id=:id AND company_id=:cid"
    ), {"id": uq_id, "cid": cid}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    db.execute(text("""
        UPDATE ai_unanswered_questions
        SET answer=:ans, answered_by=:by, answered_at=NOW(), saved_to_kb=:skb
        WHERE id=:id AND company_id=:cid
    """), {"ans": answer, "by": current_user.emp_code, "skb": save, "id": uq_id, "cid": cid})
    db.commit()
    saved_entries = []
    if save:
        saved_entries = _ai_enrich_and_save(
            company_id=cid,
            raw_input=answer,
            question=row[0],
            creator=current_user.emp_code,
            db=db,
            context_segment="",
        )
    return {"success": True, "saved_to_kb": save, "entries_saved": saved_entries}


@router.get("/unanswered-questions/count-by-log")
def unanswered_count_by_log(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Returns map of log_id → unanswered question count (for Call History badges)."""
    cid = current_user.base_company_id
    rows = db.execute(text("""
        SELECT log_id, COUNT(*) as cnt
        FROM ai_unanswered_questions
        WHERE company_id=:cid AND answer IS NULL
        GROUP BY log_id
    """), {"cid": cid}).fetchall()
    return {"success": True, "counts": {r[0]: r[1] for r in rows}}


# ─────────────────────────────────────────────────────────
# CAMPAIGN CRUD
# ─────────────────────────────────────────────────────────

@router.get("/campaigns")
def list_campaigns(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    rows = db.execute(text("""
        SELECT c.id, c.name, c.description, c.lead_filter, c.languages, c.default_language,
               c.retry_1_hours, c.retry_2_hours, c.retry_day2_offset, c.retry_day10_offset,
               c.max_concurrent, c.status, c.created_by, c.created_at, c.started_at,
               c.total_leads, c.calls_made, c.calls_connected, c.calls_qualified,
               c.ai_persona, c.campaign_segment, c.crm_status_filter,
               c.source_type, c.phone_list, c.repeat_enabled, c.repeat_count
        FROM ai_campaigns c
        WHERE c.company_id = :cid AND c.status != 'deleted'
        ORDER BY c.created_at DESC
    """), {"cid": current_user.base_company_id}).fetchall()

    campaigns = []
    for r in rows:
        cid = r[0]
        staff_rows = db.execute(text("""
            SELECT staff_emp_code, staff_name, department FROM ai_campaign_staff
            WHERE campaign_id = :cid ORDER BY assignment_order
        """), {"cid": cid}).fetchall()
        campaigns.append({
            "id": cid, "name": r[1], "description": r[2],
            "lead_filter": r[3], "languages": r[4], "default_language": r[5],
            "retry_1_hours": r[6], "retry_2_hours": r[7],
            "retry_day2_offset": r[8], "retry_day10_offset": r[9],
            "max_concurrent": r[10], "status": r[11],
            "created_by": r[12],
            "created_at": r[13].isoformat() if r[13] else None,
            "started_at": r[14].isoformat() if r[14] else None,
            "total_leads": r[15] or 0, "calls_made": r[16] or 0,
            "calls_connected": r[17] or 0, "calls_qualified": r[18] or 0,
            "ai_persona": r[19],
            "campaign_segment": r[20] or "",
            "crm_status_filter": r[21] or "",
            "source_type": r[22] or "crm",
            "phone_list": r[23] or "",
            "repeat_enabled": bool(r[24]),
            "repeat_count": int(r[25] or 1),
            "staff": [{"emp_code": s[0], "name": s[1], "department": s[2]} for s in staff_rows],
        })
    return {"success": True, "campaigns": campaigns}


@router.post("/campaigns")
def create_campaign(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Campaign name is required")
    result = db.execute(text("""
        INSERT INTO ai_campaigns
            (company_id, name, description, lead_filter, languages, default_language,
             retry_1_hours, retry_2_hours, retry_day2_offset, retry_day10_offset,
             max_concurrent, ai_persona, created_by, status, campaign_segment, crm_status_filter,
             source_type, phone_list, repeat_enabled, repeat_count)
        VALUES
            (:cid, :name, :desc, :lf, :langs, :dlang,
             :r1, :r2, :rd2, :rd10,
             :conc, :persona, :creator, 'draft', :cseg, :csf,
             :stype, :plist, :rep_en, :rep_cnt)
        RETURNING id
    """), {
        "cid": current_user.base_company_id,
        "name": name,
        "desc": payload.get("description", ""),
        "lf": payload.get("lead_filter", "untouched"),
        "langs": payload.get("languages", "hi,te,en"),
        "dlang": payload.get("default_language", "te"),
        "r1": int(payload.get("retry_1_hours", 2)),
        "r2": int(payload.get("retry_2_hours", 4)),
        "rd2": int(payload.get("retry_day2_offset", 2)),
        "rd10": int(payload.get("retry_day10_offset", 10)),
        "conc": int(payload.get("max_concurrent", 3)),
        "persona": payload.get("ai_persona", ""),
        "creator": current_user.emp_code,
        "cseg": payload.get("campaign_segment", "") or None,
        "csf": payload.get("crm_status_filter", "") or None,
        "stype": payload.get("source_type", "crm"),
        "plist": payload.get("phone_list", "") or None,
        "rep_en": bool(payload.get("repeat_enabled", False)),
        "rep_cnt": int(payload.get("repeat_count", 1) or 1),
    })
    db.commit()
    new_id = result.fetchone()[0]

    staff_list = payload.get("staff", [])
    for idx, s in enumerate(staff_list):
        emp_code = (s.get("emp_code") or "").strip()
        if not emp_code:
            continue
        db.execute(text("""
            INSERT INTO ai_campaign_staff (campaign_id, staff_emp_code, staff_name, department, assignment_order)
            VALUES (:cid, :ec, :name, :dept, :ord)
            ON CONFLICT (campaign_id, staff_emp_code) DO NOTHING
        """), {"cid": new_id, "ec": emp_code, "name": s.get("name", ""), "dept": s.get("department", ""), "ord": idx})
    db.commit()
    return {"success": True, "id": new_id, "message": "Campaign created"}


@router.put("/campaigns/{campaign_id}")
def update_campaign(
    campaign_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id, status FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    # Allow editing active campaigns — frontend shows a restart prompt after save

    allowed = ["name", "description", "lead_filter", "languages", "default_language",
               "retry_1_hours", "retry_2_hours", "retry_day2_offset", "retry_day10_offset",
               "max_concurrent", "ai_persona", "campaign_segment", "crm_status_filter",
               "source_type", "phone_list", "repeat_enabled", "repeat_count"]
    fields, params = [], {"id": campaign_id, "cid": current_user.base_company_id}
    for col in allowed:
        if col in payload:
            fields.append(f"{col} = :{col}")
            params[col] = payload[col]
    if fields:
        fields.append("updated_at = NOW()")
        db.execute(text(
            f"UPDATE ai_campaigns SET {', '.join(fields)} WHERE id=:id AND company_id=:cid"
        ), params)

    if "staff" in payload:
        db.execute(text("DELETE FROM ai_campaign_staff WHERE campaign_id=:cid"), {"cid": campaign_id})
        for idx, s in enumerate(payload["staff"]):
            emp_code = (s.get("emp_code") or "").strip()
            if emp_code:
                db.execute(text("""
                    INSERT INTO ai_campaign_staff (campaign_id, staff_emp_code, staff_name, department, assignment_order)
                    VALUES (:cid, :ec, :name, :dept, :ord)
                    ON CONFLICT (campaign_id, staff_emp_code) DO NOTHING
                """), {"cid": campaign_id, "ec": emp_code, "name": s.get("name", ""), "dept": s.get("department", ""), "ord": idx})
    db.commit()
    return {"success": True, "message": "Campaign updated"}


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id, status FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if row[1] == "active":
        raise HTTPException(status_code=400, detail="Stop the campaign before deleting")
    db.execute(text(
        "UPDATE ai_campaigns SET status='deleted', updated_at=NOW() WHERE id=:id AND company_id=:cid"
    ), {"id": campaign_id, "cid": current_user.base_company_id})
    db.commit()
    return {"success": True, "message": "Campaign deleted"}


# ─────────────────────────────────────────────────────────
# LEAD POOL PREVIEW
# ─────────────────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/leads-preview")
def preview_lead_pool(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    campaign = db.execute(text(
        "SELECT id, lead_filter, company_id, crm_status_filter, source_type, phone_list FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead_filter       = campaign[1]
    crm_status_filter = campaign[3] or ""
    source_type       = campaign[4] or "crm"
    phone_list_raw    = campaign[5] or ""

    # ── DIRECT / CSV: return parsed phone list, not CRM leads ───────────────
    if source_type in ("direct", "csv") and phone_list_raw.strip():
        phones = []
        for ph in phone_list_raw.replace("\n", ",").split(","):
            ph = ph.strip().replace(" ", "")
            if not ph:
                continue
            if not ph.startswith("+"):
                ph = "+91" + ph.lstrip("0")
            phones.append(ph)
        return {
            "success": True,
            "source_type": source_type,
            "total": len(phones),
            "filter": "direct",
            "crm_status_filter": "",
            "sample": [{"phone": ph} for ph in phones[:10]],
        }

    # ── CRM SOURCE: query crm_leads ──────────────────────────────────────────
    conditions = ["l.company_id = :cid", "l.phone IS NOT NULL"]
    params: dict = {"cid": current_user.base_company_id}

    if lead_filter == "untouched":
        conditions.append("(l.ai_call_count IS NULL OR l.ai_call_count = 0)")
        conditions.append("l.handler_type = 'unassigned'")
    elif lead_filter == "unassigned":
        conditions.append("l.handler_type = 'unassigned'")
    elif lead_filter == "never_called":
        conditions.append("l.ai_last_called_at IS NULL")
    if crm_status_filter:
        statuses = [s.strip() for s in crm_status_filter.split(",") if s.strip()]
        if statuses:
            placeholders = ", ".join(f":cs{i}" for i in range(len(statuses)))
            conditions.append(f"l.status IN ({placeholders})")
            for i, s in enumerate(statuses):
                params[f"cs{i}"] = s
    else:
        conditions.append("l.status NOT IN ('won','lost','do_not_call','completed')")

    where = " AND ".join(conditions)
    count_row = db.execute(text(f"SELECT COUNT(*) FROM crm_leads l WHERE {where}"), params).fetchone()
    sample = db.execute(text(f"""
        SELECT l.id, l.name, l.phone, l.status, l.source, l.handler_type,
               l.ai_call_count, l.ai_status
        FROM crm_leads l WHERE {where} ORDER BY l.created_at DESC LIMIT 10
    """), params).fetchall()

    return {
        "success": True,
        "source_type": "crm",
        "total": count_row[0] if count_row else 0,
        "filter": lead_filter,
        "crm_status_filter": crm_status_filter,
        "sample": [
            {"id": r[0], "name": r[1], "phone": r[2], "status": r[3],
             "source": r[4], "handler_type": r[5],
             "ai_call_count": r[6] or 0, "ai_status": r[7]}
            for r in sample
        ],
    }


# ─────────────────────────────────────────────────────────
# CAMPAIGN CONTROL
# ─────────────────────────────────────────────────────────

@router.post("/campaigns/{campaign_id}/start")
def start_campaign(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    campaign = db.execute(text("""
        SELECT id, status, lead_filter, languages, default_language, max_concurrent,
               ai_persona, company_id, campaign_segment, crm_status_filter,
               source_type, phone_list, repeat_enabled, repeat_count
        FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'
    """), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign[1] == "active":
        raise HTTPException(status_code=400, detail="Campaign already active")

    # ── On every (re)start: unstick any phantom "dialing" entries ────────────
    db.execute(text("""
        UPDATE ai_call_logs
        SET status = 'no_answer', ended_at = NOW()
        WHERE campaign_id = :cid
          AND status IN ('initiated','dialing','ringing','in-progress','connected')
    """), {"cid": campaign_id})
    db.commit()

    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
        raise HTTPException(status_code=503, detail="Twilio credentials not configured — cannot initiate calls")
    if not OPENAI_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    lead_filter       = campaign[2]
    default_lang      = campaign[4] or "te"
    max_concurrent    = int(campaign[5] or 3)
    crm_status_filter = campaign[9] or ""
    camp_segment      = campaign[8] or ""
    source_type       = campaign[10] or "crm"
    phone_list_raw    = campaign[11] or ""
    repeat_enabled    = bool(campaign[12])
    repeat_count      = int(campaign[13] or 1)

    from datetime import datetime as _dt
    run_start = _dt.utcnow()

    # ── Build lead list based on source type ──────────────────────────────────
    if source_type in ("direct", "csv") and phone_list_raw.strip():
        # Direct phone numbers — build synthetic lead objects from the list
        raw_phones_all = []
        for p in phone_list_raw.replace("\n", ",").split(","):
            p = p.strip().replace(" ", "")
            if not p:
                continue
            if not p.startswith("+"):
                p = "+91" + p.lstrip("0")
            raw_phones_all.append(p)

        leads = []
        if repeat_enabled:
            # REDIAL MODE: skip in-flight + phones already dialled repeat_count times
            in_flight_start = {
                (r[0] or "").replace(" ", "") for r in db.execute(text("""
                    SELECT phone_dialed FROM ai_call_logs
                    WHERE campaign_id = :cid
                      AND status IN ('initiated','dialing','ringing','in-progress','connected')
                """), {"cid": campaign_id}).fetchall()
            }
            dial_counts_start: dict = {}
            for r in db.execute(text("""
                SELECT phone_dialed, COUNT(*) FROM ai_call_logs
                WHERE campaign_id = :cid GROUP BY phone_dialed
            """), {"cid": campaign_id}).fetchall():
                dial_counts_start[(r[0] or "").replace(" ", "")] = int(r[1])
            for ph in raw_phones_all:
                if len(leads) >= max_concurrent:
                    break
                if ph in in_flight_start:
                    continue
                if dial_counts_start.get(ph, 0) >= repeat_count:
                    continue
                leads.append((None, ph, "", default_lang, "new"))
        else:
            # NORMAL MODE: only count dials from the CURRENT run (>= run_start)
            # — so stopping and restarting always triggers a fresh dial cycle
            already_dialed = {
                (r[0] or "").replace(" ", "") for r in db.execute(text("""
                    SELECT DISTINCT phone_dialed FROM ai_call_logs
                    WHERE campaign_id = :cid AND started_at >= :rs
                """), {"cid": campaign_id, "rs": run_start}).fetchall()
            }
            retry_eligible = {
                (r[0] or "").replace(" ", "") for r in db.execute(text("""
                    SELECT phone_dialed FROM ai_call_logs
                    WHERE campaign_id = :cid
                      AND started_at >= :rs
                      AND status IN ('no_answer', 'busy', 'failed', 'canceled')
                      AND next_retry_at IS NOT NULL AND next_retry_at <= NOW()
                """), {"cid": campaign_id, "rs": run_start}).fetchall()
            }
            skip_on_start = already_dialed - retry_eligible
            for ph in raw_phones_all:
                if len(leads) >= max_concurrent:
                    break
                if ph not in skip_on_start:
                    leads.append((None, ph, "", default_lang, "new"))
    else:
        # CRM source — query leads from database
        conditions = ["l.company_id = :cid", "l.phone IS NOT NULL"]
        params: dict = {"cid": current_user.base_company_id}
        if lead_filter == "untouched":
            conditions.extend(["(l.ai_call_count IS NULL OR l.ai_call_count = 0)", "l.handler_type = 'unassigned'"])
        elif lead_filter == "unassigned":
            conditions.append("l.handler_type = 'unassigned'")
        elif lead_filter == "never_called":
            conditions.append("l.ai_last_called_at IS NULL")
        if crm_status_filter:
            statuses = [s.strip() for s in crm_status_filter.split(",") if s.strip()]
            if statuses:
                placeholders = ", ".join(f":cs{i}" for i in range(len(statuses)))
                conditions.append(f"l.status IN ({placeholders})")
                for i, s in enumerate(statuses):
                    params[f"cs{i}"] = s
        else:
            conditions.append("l.status NOT IN ('won','lost','do_not_call','completed')")
        where = " AND ".join(conditions)
        leads = db.execute(text(
            f"SELECT l.id, l.phone, l.name, l.ai_language, l.status FROM crm_leads l WHERE {where} ORDER BY l.created_at ASC LIMIT :lim"
        ), {**params, "lim": max_concurrent}).fetchall()

    db.execute(text(
        "UPDATE ai_campaigns SET status='active', started_at=NOW(), last_started_at=:rs, updated_at=NOW() WHERE id=:id"
    ), {"id": campaign_id, "rs": run_start})
    db.commit()

    webhook_base = _webhook_base(request)
    incoming_url = f"{webhook_base}/api/v1/staff/ai-calling/webhook/voice-select"
    status_url   = f"{webhook_base}/api/v1/staff/ai-calling/webhook/status"

    initiated = 0
    errors    = []
    try:
        from twilio.rest import Client as TwilioClient
        tc = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

        for lead in leads:
            lead_id, phone, lead_name, saved_lang, lead_crm_status = lead
            # DC-LANG-FIX: Campaign default_language takes priority; lead's saved lang is fallback only.
            # Prevents previously-Hindi leads from overriding a Telugu/English campaign setting.
            lang = default_lang or saved_lang
            phone = str(phone or "").strip()
            if not phone.startswith("+"):
                phone = "+91" + phone.lstrip("0")

            try:
                log_result = db.execute(text("""
                    INSERT INTO ai_call_logs
                        (campaign_id, lead_id, company_id, phone_dialed, language_used,
                         attempt_number, status, crm_status_before)
                    VALUES (:camp, :lid, :cid, :phone, :lang,
                        COALESCE((SELECT ai_call_count FROM crm_leads WHERE id=:lid), 0) + 1,
                        'initiated', :csb)
                    RETURNING id
                """), {
                    "camp": campaign_id, "lid": lead_id,
                    "cid": current_user.base_company_id,
                    "phone": phone, "lang": lang,
                    "csb": lead_crm_status,
                })
                db.commit()
                log_id = log_result.fetchone()[0]

                seg_qp = f"&segment={_urlquote(camp_segment, safe='')}" if camp_segment else ""
                call_incoming_url = (
                    f"{incoming_url}?log_id={log_id}&lang={lang}"
                    f"&name={_urlquote(lead_name or '', safe='')}&campaign_id={campaign_id}{seg_qp}"
                )
                rec_cb = (
                    f"{webhook_base}/api/v1/staff/ai-calling/webhook/recording?log_id={log_id}"
                )
                call = tc.calls.create(
                    to=phone,
                    from_=TWILIO_FROM,
                    url=call_incoming_url,
                    status_callback=f"{status_url}?log_id={log_id}",
                    status_callback_event=["completed", "failed", "busy", "no-answer"],
                    record=True,
                    recording_status_callback=rec_cb,
                    recording_status_callback_method="POST",
                    timeout=30,
                )
                db.execute(text(
                    "UPDATE ai_call_logs SET call_sid=:sid, status='dialing' WHERE id=:id"
                ), {"sid": call.sid, "id": log_id})
                db.execute(text("""
                    UPDATE crm_leads
                    SET ai_campaign_id=:cid, ai_last_called_at=NOW(),
                        ai_call_count=COALESCE(ai_call_count,0)+1, ai_language=:lang
                    WHERE id=:lid
                """), {"cid": campaign_id, "lang": lang, "lid": lead_id})
                db.commit()
                initiated += 1
            except Exception as call_err:
                errors.append(str(call_err)[:100])
                logger.error(f"[AI_CALLING] Failed to call lead {lead_id}: {call_err}")
    except ImportError:
        raise HTTPException(status_code=503, detail="Twilio SDK not installed")

    return {
        "success": True,
        "message": f"Campaign started — {initiated} call(s) initiated",
        "initiated": initiated,
        "errors": errors[:5],
    }


@router.post("/campaigns/{campaign_id}/pause")
def pause_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id, status FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db.execute(text(
        "UPDATE ai_campaigns SET status='paused', paused_at=NOW(), updated_at=NOW() WHERE id=:id"
    ), {"id": campaign_id})
    db.commit()
    return {"success": True, "message": "Campaign paused"}


@router.post("/campaigns/{campaign_id}/stop")
def stop_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text(
        "SELECT id FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")
    db.execute(text(
        "UPDATE ai_campaigns SET status='stopped', updated_at=NOW() WHERE id=:id"
    ), {"id": campaign_id})
    db.commit()
    return {"success": True, "message": "Campaign stopped"}


# ─────────────────────────────────────────────────────────
# AUTO-DIAL LOOP — advances campaign after each call ends
# ─────────────────────────────────────────────────────────

def _try_advance_campaign(db: Session, campaign_id: int, webhook_base: str) -> None:
    """
    After any call ends for a campaign, check if we should dial the next lead(s).
    Keeps concurrency at max_concurrent until all leads are exhausted, then marks
    the campaign as 'completed'. Also picks up retry-eligible leads.
    """
    if not campaign_id:
        return
    try:
        camp = db.execute(text("""
            SELECT id, status, lead_filter, default_language, max_concurrent, company_id,
                   retry_1_hours, retry_2_hours, retry_day2_offset, retry_day10_offset,
                   crm_status_filter, campaign_segment, source_type, phone_list,
                   repeat_enabled, repeat_count, last_started_at
            FROM ai_campaigns WHERE id = :id AND status = 'active'
        """), {"id": campaign_id}).fetchone()
        if not camp:
            return

        max_concurrent    = int(camp[4] or 3)
        company_id        = camp[5]
        lead_filter       = camp[2] or "untouched"
        default_lang      = camp[3] or "te"
        crm_status_filter = camp[10] or ""
        camp_segment      = camp[11] or ""
        source_type       = camp[12] or "crm"
        phone_list_raw    = camp[13] or ""
        repeat_enabled    = bool(camp[14])
        repeat_count      = int(camp[15] or 1)
        last_started_at   = camp[16]

        # Count calls currently in-flight for this campaign
        active_count = db.execute(text("""
            SELECT COUNT(*) FROM ai_call_logs
            WHERE campaign_id = :cid AND status IN ('initiated', 'dialing', 'ringing', 'in-progress')
        """), {"cid": campaign_id}).fetchone()[0]

        slots_to_fill = max_concurrent - active_count
        if slots_to_fill <= 0:
            return

        leads_to_dial: list = []

        # ── DIRECT / CSV: advance from phone_list ─────────────────────────────
        if source_type in ("direct", "csv") and phone_list_raw.strip():
            # All phones from the list (normalised)
            all_phones = []
            for ph in phone_list_raw.replace("\n", ",").split(","):
                ph = ph.strip().replace(" ", "")
                if not ph:
                    continue
                if not ph.startswith("+"):
                    ph = "+91" + ph.lstrip("0")
                all_phones.append(ph)

            if repeat_enabled:
                # ── REDIAL MODE: allow all phones to be dialled up to repeat_count times ──
                # Phones currently in-flight — never double-dial
                in_flight_phones = {
                    (r[0] or "").replace(" ", "") for r in db.execute(text("""
                        SELECT phone_dialed FROM ai_call_logs
                        WHERE campaign_id = :cid
                          AND status IN ('initiated','dialing','ringing','in-progress','connected')
                    """), {"cid": campaign_id}).fetchall()
                }
                # Count how many times each phone has been dialled in this campaign
                dial_counts: dict = {}
                for r in db.execute(text("""
                    SELECT phone_dialed, COUNT(*) FROM ai_call_logs
                    WHERE campaign_id = :cid GROUP BY phone_dialed
                """), {"cid": campaign_id}).fetchall():
                    dial_counts[(r[0] or "").replace(" ", "")] = int(r[1])

                for ph in all_phones:
                    if len(leads_to_dial) >= slots_to_fill:
                        break
                    if ph in in_flight_phones:
                        continue
                    if dial_counts.get(ph, 0) >= repeat_count:
                        continue
                    leads_to_dial.append((None, ph, "", default_lang, "new"))

                # Done when every phone hit repeat_count AND nothing in flight
                all_done = (
                    all(dial_counts.get(ph, 0) >= repeat_count for ph in all_phones)
                    and active_count == 0
                )
            else:
                # ── NORMAL MODE: each phone dialled once per run ──────────────
                # Use last_started_at to scope to current run only;
                # stopping and restarting gives a clean dial cycle.
                from datetime import datetime as _dt2
                run_cutoff = last_started_at or _dt2(2000, 1, 1)
                all_dialed = {
                    (r[0] or "").replace(" ", "") for r in db.execute(text("""
                        SELECT DISTINCT phone_dialed FROM ai_call_logs
                        WHERE campaign_id = :cid AND started_at >= :rc
                    """), {"cid": campaign_id, "rc": run_cutoff}).fetchall()
                }
                retry_phones = {
                    (r[0] or "").replace(" ", "") for r in db.execute(text("""
                        SELECT phone_dialed FROM ai_call_logs
                        WHERE campaign_id = :cid
                          AND started_at >= :rc
                          AND status IN ('no_answer', 'busy', 'failed', 'canceled')
                          AND next_retry_at IS NOT NULL AND next_retry_at <= NOW()
                    """), {"cid": campaign_id, "rc": run_cutoff}).fetchall()
                }
                skip_phones = all_dialed - retry_phones

                for ph in all_phones:
                    if len(leads_to_dial) >= slots_to_fill:
                        break
                    if ph not in skip_phones:
                        leads_to_dial.append((None, ph, "", default_lang, "new"))

                all_done = all(ph in all_dialed for ph in all_phones)

            # Campaign complete check
            if not leads_to_dial and active_count == 0 and all_done:
                db.execute(text(
                    "UPDATE ai_campaigns SET status='completed', updated_at=NOW() WHERE id=:id"
                ), {"id": campaign_id})
                db.commit()
                logger.info(f"[AI_CALLING] Campaign {campaign_id} auto-completed — direct numbers exhausted")
                return

            if not leads_to_dial:
                return
            # Fall through to Twilio dialing code below

        else:
            # ── CRM SOURCE: advance from crm_leads ───────────────────────────
            # Build exclusion list: leads already dialed (not retry-eligible now)
            dialed_ids = [
                r[0] for r in db.execute(text("""
                    SELECT DISTINCT lead_id FROM ai_call_logs
                    WHERE campaign_id = :cid AND lead_id IS NOT NULL
                      AND (next_retry_at IS NULL OR next_retry_at > NOW())
                      AND status NOT IN ('no_answer', 'busy', 'failed', 'canceled')
                """), {"cid": campaign_id}).fetchall()
            ]

            # 1) Retry-eligible leads: previously failed, next_retry_at <= NOW()
            retry_rows = db.execute(text("""
                SELECT DISTINCT ON (lead_id) lead_id, id as log_id, language_used
                FROM ai_call_logs
                WHERE campaign_id = :cid
                  AND status IN ('no_answer', 'busy', 'failed', 'canceled')
                  AND next_retry_at IS NOT NULL
                  AND next_retry_at <= NOW()
                  AND lead_id IS NOT NULL
                ORDER BY lead_id, next_retry_at ASC
                LIMIT :lim
            """), {"cid": campaign_id, "lim": slots_to_fill}).fetchall()

            for rr in retry_rows:
                if len(leads_to_dial) >= slots_to_fill:
                    break
                lead = db.execute(text("""
                    SELECT id, phone, name, ai_language, status
                    FROM crm_leads
                    WHERE id = :lid AND status NOT IN ('won', 'lost', 'do_not_call')
                      AND phone IS NOT NULL
                """), {"lid": rr[0]}).fetchone()
                if lead:
                    leads_to_dial.append((lead[0], lead[1], lead[2], rr[2] or lead[3], lead[4]))
                    db.execute(text(
                        "UPDATE ai_call_logs SET next_retry_at = NULL WHERE id = :id"
                    ), {"id": rr[1]})

            # 2) Fresh leads not yet dialed in this campaign
            if len(leads_to_dial) < slots_to_fill:
                remaining = slots_to_fill - len(leads_to_dial)
                conditions = ["l.company_id = :cid", "l.phone IS NOT NULL"]
                fresh_params: dict = {"cid": company_id}
                all_dialed_ids = dialed_ids + [x[0] for x in leads_to_dial]
                if all_dialed_ids:
                    id_placeholders = ",".join(str(i) for i in all_dialed_ids)
                    conditions.append(f"l.id NOT IN ({id_placeholders})")
                if lead_filter == "untouched":
                    conditions.extend([
                        "(l.ai_call_count IS NULL OR l.ai_call_count = 0)",
                        "l.handler_type = 'unassigned'",
                    ])
                elif lead_filter == "unassigned":
                    conditions.append("l.handler_type = 'unassigned'")
                elif lead_filter == "never_called":
                    conditions.append("l.ai_last_called_at IS NULL")
                if crm_status_filter:
                    sf_statuses = [s.strip() for s in crm_status_filter.split(",") if s.strip()]
                    if sf_statuses:
                        sf_placeholders = ", ".join(f":sf{i}" for i in range(len(sf_statuses)))
                        conditions.append(f"l.status IN ({sf_placeholders})")
                        for i, s in enumerate(sf_statuses):
                            fresh_params[f"sf{i}"] = s
                else:
                    conditions.append("l.status NOT IN ('won','lost','do_not_call','completed')")
                where = " AND ".join(conditions)
                fresh = db.execute(text(
                    f"SELECT l.id, l.phone, l.name, l.ai_language, l.status FROM crm_leads l"
                    f" WHERE {where} ORDER BY l.created_at ASC LIMIT :lim"
                ), {**fresh_params, "lim": remaining}).fetchall()
                leads_to_dial.extend((r[0], r[1], r[2], r[3], r[4]) for r in fresh)

            # If no leads remain and nothing in flight → campaign complete
            if not leads_to_dial and active_count == 0:
                db.execute(text(
                    "UPDATE ai_campaigns SET status='completed', updated_at=NOW() WHERE id=:id"
                ), {"id": campaign_id})
                db.commit()
                logger.info(f"[AI_CALLING] Campaign {campaign_id} auto-completed — leads exhausted")
                return

            if not leads_to_dial:
                return

        db.commit()  # Commit next_retry_at nullifications

        incoming_url = f"{webhook_base}/api/v1/staff/ai-calling/webhook/voice-select"
        status_url   = f"{webhook_base}/api/v1/staff/ai-calling/webhook/status"

        from twilio.rest import Client as TwilioClient
        tc = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

        for (lead_id, phone, lead_name, saved_lang, lead_crm_status) in leads_to_dial:
            # DC-LANG-FIX: Campaign language has priority over lead's saved language.
            lang  = default_lang or saved_lang
            phone = str(phone or "").strip()
            if not phone.startswith("+"):
                phone = "+91" + phone.lstrip("0")
            try:
                log_result = db.execute(text("""
                    INSERT INTO ai_call_logs
                        (campaign_id, lead_id, company_id, phone_dialed, language_used,
                         attempt_number, status, crm_status_before)
                    VALUES (:camp, :lid, :cid, :phone, :lang,
                        COALESCE((SELECT MAX(attempt_number) FROM ai_call_logs
                                  WHERE lead_id=:lid AND campaign_id=:camp), 0) + 1,
                        'initiated', :csb)
                    RETURNING id
                """), {
                    "camp": campaign_id, "lid": lead_id, "cid": company_id,
                    "phone": phone, "lang": lang, "csb": lead_crm_status,
                })
                db.commit()
                log_id = log_result.fetchone()[0]

                rec_cb2 = (
                    f"{webhook_base}/api/v1/staff/ai-calling/webhook/recording?log_id={log_id}"
                )
                seg_param = f"&segment={_urlquote(camp_segment, safe='')}" if camp_segment else ""
                call = tc.calls.create(
                    to=phone,
                    from_=TWILIO_FROM,
                    url=(f"{incoming_url}?log_id={log_id}&lang={lang}"
                         f"&name={_urlquote(lead_name or '', safe='')}&campaign_id={campaign_id}{seg_param}"),
                    status_callback=f"{status_url}?log_id={log_id}",
                    status_callback_event=["completed", "failed", "busy", "no-answer"],
                    record=True,
                    recording_status_callback=rec_cb2,
                    recording_status_callback_method="POST",
                    timeout=30,
                )
                db.execute(text(
                    "UPDATE ai_call_logs SET call_sid=:sid, status='dialing' WHERE id=:id"
                ), {"sid": call.sid, "id": log_id})
                db.execute(text("""
                    UPDATE crm_leads
                    SET ai_campaign_id=:campid, ai_last_called_at=NOW(),
                        ai_call_count=COALESCE(ai_call_count,0)+1, ai_language=:lang
                    WHERE id=:lid
                """), {"campid": campaign_id, "lang": lang, "lid": lead_id})
                db.commit()
                logger.info(f"[AI_CALLING] Auto-advance: dialed lead {lead_id}, log {log_id}")
            except Exception as call_err:
                logger.error(f"[AI_CALLING] Auto-advance call failed for lead {lead_id}: {call_err}")

    except Exception as e:
        logger.error(f"[AI_CALLING] _try_advance_campaign error for campaign {campaign_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────
# TEST CALL
# ─────────────────────────────────────────────────────────

@router.post("/test-call")
def make_test_call(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Place a single test call to any phone number with chosen language + segment."""
    phone    = str(payload.get("phone", "")).strip()
    language = payload.get("language", "hi")
    segment  = payload.get("segment", "")
    name     = payload.get("name", "Test").strip() or "Test"

    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")

    if not TWILIO_SID or not TWILIO_TOKEN or not TWILIO_FROM:
        raise HTTPException(status_code=503, detail="Twilio credentials not configured")
    if not OPENAI_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    log_result = db.execute(text("""
        INSERT INTO ai_call_logs
            (campaign_id, lead_id, company_id, phone_dialed, language_used, attempt_number, status, segment)
        VALUES (NULL, NULL, :cid, :phone, :lang, 1, 'initiated', :seg)
        RETURNING id
    """), {
        "cid": current_user.base_company_id,
        "phone": phone,
        "lang": language,
        "seg": segment or None,
    })
    db.commit()
    log_id = log_result.fetchone()[0]

    webhook_base = _webhook_base(request)
    seg_qs = f"&segment={_urlquote(segment, safe='')}" if segment else ""
    # ── Voice-select is the new entry point — greeting TTS generated after customer picks agent ──
    incoming_url = (
        f"{webhook_base}/api/v1/staff/ai-calling/webhook/voice-select"
        f"?log_id={log_id}&lang={language}&name={_urlquote(name, safe='')}&campaign_id=0&is_test=1{seg_qs}"
    )
    status_url = f"{webhook_base}/api/v1/staff/ai-calling/webhook/status?log_id={log_id}"

    try:
        from twilio.rest import Client as TwilioClient
        tc = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        recording_url = (
            f"{webhook_base}/api/v1/staff/ai-calling/webhook/recording?log_id={log_id}"
        )
        call = tc.calls.create(
            to=phone,
            from_=TWILIO_FROM,
            url=incoming_url,
            status_callback=status_url,
            status_callback_event=["completed", "failed", "busy", "no-answer"],
            record=True,
            recording_status_callback=recording_url,
            recording_status_callback_method="POST",
            timeout=30,
        )
        db.execute(text(
            "UPDATE ai_call_logs SET call_sid=:sid, status='dialing' WHERE id=:id"
        ), {"sid": call.sid, "id": log_id})
        db.commit()
        return {
            "success": True,
            "message": f"Test call initiated to {phone}",
            "log_id": log_id,
            "call_sid": call.sid,
            "language": language,
            "segment": segment or "All segments",
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="Twilio SDK not installed")
    except Exception as e:
        db.execute(text("UPDATE ai_call_logs SET status='failed' WHERE id=:id"), {"id": log_id})
        db.commit()
        import re as _re
        raw = str(e)
        clean = _re.sub(r'\x1b\[[0-9;]*m', '', raw)
        cl = clean.lower()

        # ── Extract Twilio error code if present ──
        code_match = _re.search(r'\b(2\d{4})\b', clean)
        twilio_code = code_match.group(1) if code_match else ""

        # ── Geographic permissions (most common India calling failure) ──
        if twilio_code in ("21215", "21217") or "permission" in cl or "geo" in cl or "not enabled" in cl or "international" in cl:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Twilio geographic permission denied (code {twilio_code or 'N/A'}). "
                    "India (+91) calling is not enabled on your Twilio account. "
                    "Fix: Twilio Console → Voice → Geographic Permissions → enable India."
                )
            )
        # ── Trial account — unverified destination ──
        if twilio_code == "21608" or "unverified" in cl or "trial" in cl:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Twilio trial account restriction (code {twilio_code}): "
                    "You can only call verified numbers. "
                    "Fix: Twilio Console → Verify → Add a verified caller ID for the destination number, "
                    "or upgrade your Twilio account."
                )
            )
        # ── Do-Not-Originate list ──
        if "do-not-originate" in cl or "dno" in cl or twilio_code == "21212":
            raise HTTPException(
                status_code=400,
                detail=f"Twilio DNO: {TWILIO_FROM} is blocked by carriers as a caller ID. Update TWILIO_PHONE_NUMBER with a different verified number."
            )
        # ── Invalid From number ──
        if twilio_code in ("21201", "21210") or ("not a valid" in cl and "from" in cl):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Twilio 'From' number {TWILIO_FROM} (code {twilio_code}). Verify it is active in your Twilio console."
            )
        # ── Pass-through: show the real Twilio error ──
        raise HTTPException(status_code=400, detail=f"Twilio error: {clean}")


@router.post("/leads/{lead_id}/reset-ai-preference")
def reset_lead_ai_preference(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """DC-LANG-FIX E: Clear a lead's saved AI language / agent / voice preference.
    After reset the returning-caller shortcut will not fire for this lead and the
    customer will experience the full language + agent selection IVR on the next call.
    """
    result = db.execute(text("""
        UPDATE crm_leads
        SET ai_language        = NULL,
            ai_preferred_agent = NULL,
            ai_preferred_voice = NULL
        WHERE id = :lid
          AND company_id = :cid
        RETURNING id
    """), {"lid": lead_id, "cid": current_user.base_company_id})
    db.commit()
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Lead not found or not in your company")
    logger.info(f"[AI-CALLING] AI preference reset for lead {lead_id} by {current_user.emp_code}")
    return {"success": True, "message": "AI preference cleared — next call will use fresh language/agent selection"}


# ─────────────────────────────────────────────────────────
# TWILIO WEBHOOK — VOICE SELECTION (new entry point for all calls)
# ─────────────────────────────────────────────────────────

# Lead sources that imply a prior direct enquiry by the caller
_ENQUIRY_SOURCES = {
    "online", "website", "portal", "99acres", "magicbricks", "makaan",
    "housing", "sulekha", "justdial", "google", "facebook", "instagram",
    "whatsapp", "enquiry", "digital", "form", "campaign",
}


def _get_lead_source_type(db: Session, log_id: int) -> str:
    """Return 'enquiry', 'reference', or 'cold' for a lead linked to a call log.

    'enquiry'   → caller explicitly filled a form / came via a digital channel
    'reference' → someone else referred this person (they may not know about enquiry)
    'cold'      → no source or bulk/cold outreach — safest to use neutral intro
    """
    try:
        row = db.execute(text("""
            SELECT l.source FROM crm_leads l
            JOIN ai_call_logs cl ON cl.lead_id = l.id
            WHERE cl.id = :lid
        """), {"lid": log_id}).fetchone()
        if not row or not row[0]:
            return "cold"
        src = (row[0] or "").lower().strip()
        if any(k in src for k in ("refer", "ref ", "referral", "friend", "family")):
            return "reference"
        if any(k in src for k in _ENQUIRY_SOURCES):
            return "enquiry"
        return "cold"
    except Exception:
        return "cold"


def _segment_kind(segment: str) -> str:
    """Classify segment string into a pitch category."""
    s = (segment or "").lower()
    if any(k in s for k in ("solar", "surya", "rooftop", "pm surya")):
        return "solar"
    if any(k in s for k in ("ev", "zynova", "battery", "spare", "motor", "charger", "electric vehicle")):
        return "ev"
    if any(k in s for k in ("myntreal hub", "hub")):
        return "hub"
    if any(k in s for k in ("residential", "apartment", "flat", "villa", "plot", "property", "real estate", "housing")):
        return "realty"
    return "general"


def _segment_agent_intro(kind: str, agent_name: str, lang: str) -> str:
    """Return a short segment-specific identity phrase for the system prompt opening."""
    is_male = agent_name.lower() == "karthik"
    _g = "raha" if is_male else "rahi"
    if kind == "solar":
        return {
            "hi": f"aap ek certified solar energy specialist hain jo PM Pradhan Mantri Surya Ghar Yojana ke tahat homeowners ko solar rooftop lagaane aur ₹78,000 tak ki government subsidy dilwaane mein help karte hain. Aap VGK Real Dreams ke solar division ke liye kaam karte hain.",
            "te": f"meeru PM Pradhan Mantri Surya Ghar Yojana kinda homeowners ki solar rooftop pettukoni ₹78,000 varaku government subsidy vastulaago cheyyataaniki help chese certified solar energy specialist ga pani chestunnaaru. Meeru VGK Real Dreams solar division lo pani chestunnaaru.",
            "en": f"you are a certified solar energy specialist helping homeowners set up rooftop solar panels and claim up to ₹78,000 in government subsidy under the PM Surya Ghar Yojana scheme. You work for the solar division of VGK Real Dreams.",
        }.get(lang, "")
    if kind == "ev":
        return {
            "hi": f"aap Zynova EV Marketplace ke specialist hain — EV batteries, chargers, motors aur spare parts ke expert. Aap customers ko unke EV vehicle ke liye sahi parts dhundhne mein help karte hain.",
            "te": f"meeru Zynova EV Marketplace specialist ga, EV batteries, chargers, motors mariyu spare parts expert ga pani chestunnaaru. Customers ki vaaḷḷa EV vehicle ki correct parts find avataniki help chestunnaaru.",
            "en": f"you are a specialist at Zynova EV Marketplace — expert in EV batteries, chargers, motors and spare parts, helping customers find the right components for their electric vehicles.",
        }.get(lang, "")
    if kind == "hub":
        return {
            "hi": f"aap Mynt Real LLP / VGK Real Dreams ke senior property consultant hain — Visakhapatnam ke Myntreal Hub project ke specialist, 6 saal ke experience ke saath.",
            "te": f"meeru Mynt Real LLP / VGK Real Dreams lo senior property consultant ga, Visakhapatnam lo Myntreal Hub project specialist ga 6 sallala experience tho pani chestunnaaru.",
            "en": f"you are a senior property consultant at Mynt Real LLP / VGK Real Dreams, specialising in the Myntreal Hub project in Visakhapatnam, with 6 years of experience.",
        }.get(lang, "")
    # realty or general
    return {
        "hi": f"aap Mynt Real LLP / VGK Real Dreams ke senior property consultant hain — Visakhapatnam mein residential properties ke expert, 6 saal ke experience ke saath.",
        "te": f"meeru Mynt Real LLP / VGK Real Dreams lo senior property consultant ga, Visakhapatnam lo residential properties expert ga 6 sallala experience tho pani chestunnaaru.",
        "en": f"you are a senior property consultant at Mynt Real LLP / VGK Real Dreams, an expert in residential real estate in Visakhapatnam, with 6 years of experience.",
    }.get(lang, "")


def _build_greeting(
    agent_name: str, lang: str, name: str, segment: str,
    source_type: str = "enquiry"
) -> str:
    """Build the correct greeting based on lead source type AND segment.

    source_type:
      'enquiry'   → "Aapne enquiry ki thi …"
      'reference' → neutral intro without assuming caller knows about the company
      'cold'      → cold intro with segment-specific pitch hook
    """
    is_male   = agent_name.lower() == "karthik"
    kind      = _segment_kind(segment)

    # ── Time-based greeting ───────────────────────────────────────────────────
    _ist_hour = datetime.now(IST).hour
    if _ist_hour < 12:
        _wish_te = "Subhodayam"
        _wish_hi = "Suprabhat"
        _wish_en = "Good morning"
    elif _ist_hour < 17:
        _wish_te = "Namaskaram"
        _wish_hi = "Namaste"
        _wish_en = "Good afternoon"
    else:
        _wish_te = "Namaskaram"
        _wish_hi = "Namaste"
        _wish_en = "Good evening"

    # ── Language-specific name + honorific parts ──────────────────────────────
    # Telugu  → "<Name> garu"  (gender-neutral respectful suffix)
    # Hindi   → "<Name>"       ("ji" already appended in the template string itself)
    # English → "<Name>"       (plain; sir/ma'am used during conversation by GPT)
    name_part_te = f" {name} garu" if name else ""
    name_part_hi = f" {name}"     if name else ""
    name_part_en = f" {name}"     if name else ""

    # ── Segment-specific intro phrases ───────────────────────────────────────
    if kind == "solar":
        _brand_hi = "PM Surya Ghar Yojana — solar rooftop solutions ke baare mein"
        _brand_te = "PM Surya Ghar Yojana — solar rooftop solutions gurinchi"
        _brand_en = "about the PM Surya Ghar Yojana solar rooftop scheme"
        _hook_hi  = "Sarkaar ₹78,000 tak ki subsidy de rahi hai — iske baare mein baat karni thi. Ek do minute milenge?"
        _hook_te  = "Government ₹78,000 varaku subsidy istundi — dani gurinchi matladali anukuntunna. Rendu nimishalu untaayi kaa?"
        _hook_en  = "The government offers up to ₹78,000 in subsidy — I'd love to share details. Do you have a couple of minutes?"
        _from_hi  = "VGK Real Dreams solar division se"
        _from_te  = "VGK Real Dreams solar division nundi"
        _from_en  = "from VGK Real Dreams solar division"
    elif kind == "ev":
        _brand_hi = "Zynova EV Marketplace se — EV spare parts ke baare mein"
        _brand_te = "Zynova EV Marketplace nundi — EV spare parts gurinchi"
        _brand_en = "from Zynova EV Marketplace — about EV spare parts"
        _hook_hi  = "Aapke EV vehicle ke liye sahi parts milwaane ke baare mein baat karni thi. Ek minute milega?"
        _hook_te  = "Mee EV vehicle ki correct parts gurinchi matladali anukuntunna. Oka nimisha untaayi kaa?"
        _hook_en  = "I wanted to discuss EV parts for your vehicle. Do you have a minute?"
        _from_hi  = "Zynova EV Marketplace se"
        _from_te  = "Zynova EV Marketplace nundi"
        _from_en  = "from Zynova EV Marketplace"
    elif kind == "hub":
        _seg_label = segment or "Myntreal Hub"
        _brand_hi = f"Mynt Real LLP se — {_seg_label} project ke baare mein"
        _brand_te = f"Mynt Real LLP nundi — {_seg_label} project gurinchi"
        _brand_en = f"from Mynt Real LLP — about the {_seg_label} project"
        _hook_hi  = "Visakhapatnam mein ek premium residential project ke baare mein details share karni thi. Thodi der baat kar sakte hain?"
        _hook_te  = "Visakhapatnam lo oka premium residential project details share chesukodaaniki call chesaanu. Matladagalara?"
        _hook_en  = "I wanted to share details about a premium residential project in Visakhapatnam. Is this a good time?"
        _from_hi  = "Mynt Real LLP se"
        _from_te  = "Mynt Real LLP nundi"
        _from_en  = "from Mynt Real LLP"
    else:  # realty / general
        _seg_label = segment or ""
        _seg_suffix_hi = f"{_seg_label} project ke baare mein" if _seg_label else "residential properties ke baare mein"
        _seg_suffix_te = f"{_seg_label} project gurinchi" if _seg_label else "residential properties gurinchi"
        _seg_suffix_en = f"about {_seg_label}" if _seg_label else "about our residential projects"
        _brand_hi = f"Mynt Real LLP se — {_seg_suffix_hi}"
        _brand_te = f"Mynt Real LLP nundi — {_seg_suffix_te}"
        _brand_en = f"from Mynt Real LLP — {_seg_suffix_en}"
        _hook_hi  = "Visakhapatnam mein aapke liye sahi property option share karni thi. Kya thodi der baat kar sakte hain?"
        _hook_te  = "Visakhapatnam lo mee ki sari property option share chesukodaaniki call chesaanu. Matladagalara?"
        _hook_en  = "I wanted to share some property options suited for you in Visakhapatnam. Is this a good time?"
        _from_hi  = "Mynt Real LLP se"
        _from_te  = "Mynt Real LLP nundi"
        _from_en  = "from Mynt Real LLP"

    if source_type == "enquiry":
        _enq_hi = f"Aapne humse {_brand_hi.split('—')[1].strip() if '—' in _brand_hi else _brand_hi} enquiry ki thi, to aaj personally follow up karne ke liye call kar {'raha' if is_male else 'rahi'} hoon — kya aap thodi der baat kar sakte hain?"
        _enq_te = f"Meeru maa tho {_brand_te.split('—')[1].strip() if '—' in _brand_te else _brand_te} enquiry chesaaru, kaabatti personally follow up chesaanu — ippudu matladataama?"
        _enq_en = f"You had enquired with us {_brand_en.split('—')[1].strip() if '—' in _brand_en else _brand_en}, and I'm following up personally — is this a good time to talk?"
        if is_male:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Karthik bol raha hoon {_from_hi}. {_enq_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Karthik ni, {_from_te} matladutunna. {_enq_te}",
                "en": f"{_wish_en}{name_part_en}! This is Karthik calling {_from_en}. {_enq_en}",
            }.get(lang, "")
        else:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Vidya bol rahi hoon {_from_hi}. {_enq_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Vidya ni, {_from_te} matladutunna. {_enq_te}",
                "en": f"{_wish_en}{name_part_en}! This is Vidya calling {_from_en}. {_enq_en}",
            }.get(lang, "")

    elif source_type == "reference":
        if is_male:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Karthik bol raha hoon {_from_hi} — {_brand_hi.split('—')[1].strip() if '—' in _brand_hi else _brand_hi}. Aapka number hamare ek associate ne share kiya tha. {_hook_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Karthik ni, {_from_te} matladutunna — {_brand_te.split('—')[1].strip() if '—' in _brand_te else _brand_te}. Mee number maa associate share chesaaru. {_hook_te}",
                "en": f"{_wish_en}{name_part_en}! This is Karthik {_from_en} — {_brand_en.split('—')[1].strip() if '—' in _brand_en else _brand_en}. One of our associates shared your number. {_hook_en}",
            }.get(lang, "")
        else:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Vidya bol rahi hoon {_from_hi} — {_brand_hi.split('—')[1].strip() if '—' in _brand_hi else _brand_hi}. Aapka number hamare ek associate ne share kiya tha. {_hook_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Vidya ni, {_from_te} matladutunna — {_brand_te.split('—')[1].strip() if '—' in _brand_te else _brand_te}. Mee number maa associate share chesaaru. {_hook_te}",
                "en": f"{_wish_en}{name_part_en}! This is Vidya {_from_en} — {_brand_en.split('—')[1].strip() if '—' in _brand_en else _brand_en}. One of our associates shared your number. {_hook_en}",
            }.get(lang, "")

    else:  # cold
        if is_male:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Karthik bol raha hoon {_from_hi}. {_hook_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Karthik ni, {_from_te} matladutunna. {_hook_te}",
                "en": f"{_wish_en}{name_part_en}! This is Karthik {_from_en}. {_hook_en}",
            }.get(lang, "")
        else:
            return {
                "hi": f"{_wish_hi}{name_part_hi} ji! Main Vidya bol rahi hoon {_from_hi}. {_hook_hi}",
                "te": f"{_wish_te}{name_part_te}! Nenu Vidya ni, {_from_te} matladutunna. {_hook_te}",
                "en": f"{_wish_en}{name_part_en}! This is Vidya {_from_en}. {_hook_en}",
            }.get(lang, "")


def _twiml_error_hangup(lang: str = "hi") -> Response:
    """Return a graceful TwiML response when a webhook crashes unexpectedly.
    Caller hears a polite 'technical difficulty' message and the call ends cleanly."""
    messages = {
        "hi": "Maafi chahte hain, abhi kuch technical samasya aa gayi hai. Hum jald hi wapas call karenge.",
        "te": "Mannam cheyandi, ippudu kొంcht technical samasya vastondi. Meeru mariyu call chestamu.",
        "en": "We apologise for the inconvenience. A technical issue has occurred. We will call you back shortly.",
    }
    msg = messages.get(lang, messages["hi"])
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="Polly.Aditi" language="hi-IN">{msg}</Say>'
        "<Hangup/>"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


def _get_campaign_persona(db: Session, campaign_id: int) -> tuple:
    """Return (agent_name, tts_voice, segment) from campaign settings.
    Returns (None, None, "") if no preset or campaign not found."""
    if not campaign_id:
        return None, None, ""
    try:
        row = db.execute(text("""
            SELECT ai_persona, campaign_segment FROM ai_campaigns WHERE id = :id
        """), {"id": campaign_id}).fetchone()
        if not row or not row[0]:
            return None, None, (row[1] or "") if row else ""
        pname = (row[0] or "").strip().lower()
        segment = (row[1] or "") if row else ""
        if "karthik" in pname:
            return "Karthik", "onyx", segment
        return "Vidya", "nova", segment
    except Exception:
        return None, None, ""


def _detect_voice_choice(speech: str) -> tuple:
    """Returns (agent_name, tts_voice) based on customer's spoken choice.
    Returns (None, None) if no clear signal — caller will fall back to campaign preset or default."""
    s = speech.lower()
    # Male / Karthik signals
    if any(w in s for w in ("karthik", "male", "gents", "anna", "bhai", "brother",
                             "sir", "man", "uncle", "boys", "boy", "he ", "him")):
        return "Karthik", "onyx"
    # Female / Vidya signals
    if any(w in s for w in ("vidya", "lady", "female", "madam", "ladies", "woman",
                             "akka", "sister", "amma", "she ", "her")):
        return "Vidya", "nova"
    # No clear signal — let caller preset / campaign preset decide
    return None, None


def _detect_pref_change(speech: str):
    """
    Detects if a caller is explicitly requesting a different language or agent
    mid-conversation.  Returns:
      ("agent", agent_name, tts_voice)  — caller wants a specific agent
      ("lang",  lang_code)              — caller wants a specific language
      None                              — no explicit change detected
    Checked BEFORE GPT so we can save the new preference and let GPT naturally
    adapt (system prompt will carry the updated agent name / language).
    """
    s_raw = speech or ""
    s = s_raw.lower()

    # --- explicit agent switch signals ---
    wants_karthik = any(w in s for w in (
        "karthik", "male agent", "male wala", "bhai se", "anna se",
        "gent se", "man se", "male voice", "karthik chahiye", "karthik se",
    ))
    wants_vidya = any(w in s for w in (
        "vidya", "lady agent", "lady wali", "akka se", "amma se",
        "female agent", "female se", "madam se", "woman se", "vidya chahiye",
        "vidya se",
    ))
    if wants_karthik and not wants_vidya:
        return ("agent", "Karthik", "onyx")
    if wants_vidya and not wants_karthik:
        return ("agent", "Vidya", "nova")

    # --- explicit language switch — romanized keywords (any language context) ---
    # Telugu
    if any(k in s for k in ("telugu lo", "telugu mein", "telugu me", "telugu karo",
                              "telugu chahiye", "telugu bol", "telugu matladandi",
                              "telugu lo matl", "telugu lo baat", "telugu please",
                              "in telugu", "speak telugu")):
        return ("lang", "te")
    # Hindi
    if any(k in s for k in ("hindi mein", "hindi me", "hindi lo", "hindi boliye",
                              "hindi karo", "hindi chahiye", "hindi bol",
                              "in hindi", "speak hindi", "hindi please")):
        return ("lang", "hi")
    # English
    if any(k in s for k in ("english mein", "english me", "english lo", "english karo",
                              "english chahiye", "speak english", "english please",
                              "english bol", "in english", "talk english")):
        return ("lang", "en")

    # --- Unicode-script based language-change signals ---
    # When STT (hi-IN) transcribes in native script, check for native "change to X" patterns
    # Telugu Unicode range: 0C00–0C7F
    te_chars = sum(1 for c in s_raw if 0x0C00 <= ord(c) <= 0x0C7F)
    hi_chars = sum(1 for c in s_raw if 0x0900 <= ord(c) <= 0x097F)
    if te_chars > 3:
        # Phrases indicating language-switch in Telugu: "తెలుగులో చెప్పండి" etc.
        if any(k in s_raw for k in ("తెలుగు", "తెలుగులో", "తెలుగు లో")):
            return ("lang", "te")
    if hi_chars > 3:
        # Hindi Unicode language switch: "हिंदी में बोलिए" etc.
        if any(k in s_raw for k in ("हिंदी", "हिन्दी", "हिंदी में", "हिन्दी में")):
            return ("lang", "hi")

    # --- Bare language word (caller just says the language name mid-call) ---
    s_bare = s.strip(".,!? ")
    if s_bare in ("telugu", "te", "andhra", "telgu", "telugo"):
        return ("lang", "te")
    if s_bare in ("hindi", "hi", "hind", "hindhi"):
        return ("lang", "hi")
    if s_bare in ("english", "en", "eng", "angrezi"):
        return ("lang", "en")

    return None


def _detect_language(speech: str) -> str:
    """Detects preferred language from caller's spoken choice.
    Returns 'hi' (Hindi), 'te' (Telugu), or 'en' (English). Default: 'hi'.
    """
    s = (speech or "").lower().strip()
    # Telugu signals (check before Hindi to avoid partial overlaps)
    if any(k in s for k in ("telugu", "tel ", "telgu", "telugo", "teglu",
                              "andhra", "nenu", "meeru", "andi", "రు", "తె")):
        return "te"
    # English signals
    if any(k in s for k in ("english", "eng ", "angrezi", "inglis", "inglish",
                              "angl", "ingrezi")):
        return "en"
    # Hindi signals
    if any(k in s for k in ("hindi", "hind ", "hindhi", "hindee", "हिंदी", "हिन्दी")):
        return "hi"
    # Bare single-word matches
    s_bare = s.strip(".,!? ")
    if s_bare in ("telugu", "te", "andhra"):   return "te"
    if s_bare in ("english", "en", "eng"):      return "en"
    if s_bare in ("hindi", "hi", "hind"):       return "hi"
    return "hi"  # default to Hindi


@router.post("/webhook/voice-select")
async def webhook_voice_select(
    request: Request,
    log_id: int = Query(...),
    lang: str = Query("hi"),
    name: str = Query(""),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    STEP 1 — Entry point for every call.
    Asks the customer to choose their preferred language: Hindi / Telugu / English.
    Speech is sent to /webhook/lang-confirm which detects the choice and asks
    for agent selection (Vidya / Karthik) in the detected language.
    """
    form_data = await request.form()
    call_sid  = form_data.get("CallSid", "")

    # Mark call connected; create session — pre-load campaign persona if set
    db.execute(text(
        "UPDATE ai_call_logs SET status='connected', call_sid=:sid WHERE id=:id"
    ), {"id": log_id, "sid": call_sid})

    # Fetch campaign preset persona + segment (if not already passed in URL)
    preset_agent, preset_voice, camp_segment = _get_campaign_persona(db, campaign_id)
    init_agent = preset_agent or "Vidya"
    init_voice = preset_voice or "nova"
    # Use URL-passed segment first; fall back to campaign segment
    effective_segment = segment or camp_segment or ""

    db.execute(text("""
        INSERT INTO ai_call_sessions
            (call_sid, campaign_id, log_id, lead_id, language, conversation, agent_voice, agent_name)
        SELECT :sid, NULLIF(:camp, 0), :lid, cl.lead_id, :lang, :conv, :voice, :aname
        FROM ai_call_logs cl WHERE cl.id = :lid
        ON CONFLICT (call_sid) DO UPDATE
            SET language = EXCLUDED.language,
                agent_voice = EXCLUDED.agent_voice,
                agent_name  = EXCLUDED.agent_name
    """), {
        "sid": call_sid, "camp": campaign_id, "lid": log_id, "lang": lang,
        "conv": json.dumps([]), "voice": init_voice, "aname": init_agent,
    })
    db.commit()

    base       = _webhook_base(request)
    seg_qs     = f"&amp;segment={_urlquote(effective_segment, safe='')}" if effective_segment else ""
    is_test_qs = f"&amp;is_test={is_test}" if is_test else ""

    # ── RETURNING CALLER: skip selection if preferences saved ──────────────────
    # Look up this lead's saved lang + agent choice from their last call.
    pref_row = db.execute(text("""
        SELECT cl.ai_language, cl.ai_preferred_agent, cl.ai_preferred_voice
        FROM ai_call_logs l
        JOIN crm_leads cl ON cl.id = l.lead_id
        WHERE l.id = :lid AND cl.ai_preferred_agent IS NOT NULL
              AND cl.ai_language IS NOT NULL
    """), {"lid": log_id}).fetchone()

    # DC-LANG-FIX B: Test calls always skip the returning-caller shortcut so the
    # tester experiences the full selected-language flow without a Hindi override.
    # Campaign calls honour the URL ?lang= (which is already the campaign language
    # after Fix A) but still respect the customer's saved agent/voice preference.
    if pref_row and pref_row[0] and pref_row[1] and pref_row[2] and not is_test:
        # ── Returning caller: use campaign-selected language, keep saved agent/voice ──
        # Use the URL ?lang= (= campaign default_language) instead of the lead's saved
        # ai_language so a Telugu campaign cannot be overridden by a prior Hindi call.
        saved_lang   = lang           # ← Campaign/URL language takes priority
        saved_agent  = pref_row[1]    # ← Customer's preferred agent is preserved
        saved_voice  = pref_row[2]    # ← Customer's preferred voice is preserved
        twilio_lang  = LANG_MAP.get(saved_lang, "hi-IN")

        # Update session with saved preferences immediately
        db.execute(text("""
            UPDATE ai_call_sessions
            SET language = :lang, agent_voice = :voice, agent_name = :aname,
                updated_at = NOW()
            WHERE log_id = :lid
        """), {"lang": saved_lang, "voice": saved_voice, "aname": saved_agent, "lid": log_id})
        db.commit()

        # Build greeting for saved agent — respect lead source for intro phrasing
        source_type = _get_lead_source_type(db, log_id)
        greeting = _build_greeting(saved_agent, saved_lang, name, effective_segment, source_type)
        if not greeting:
            greeting = _build_greeting(saved_agent, "en", name, effective_segment, source_type)

        db.execute(text("""
            UPDATE ai_call_sessions
            SET conversation = :conv, updated_at = NOW()
            WHERE log_id = :lid
        """), {"conv": json.dumps([{"role": "assistant", "content": greeting}]), "lid": log_id})
        db.commit()

        respond_url = (
            f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
            f"?lang={saved_lang}&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
        )

        safe_greeting = greeting.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        greeting_block = f'<Say voice="Polly.Aditi">{safe_greeting}</Say>'
        try:
            greeting_audio = await asyncio.wait_for(
                asyncio.to_thread(_generate_tts, greeting, saved_lang, saved_voice),
                timeout=11.0,
            )
            if greeting_audio and os.path.exists(os.path.join(AI_AUDIO_DIR, greeting_audio)) \
                    and os.path.getsize(os.path.join(AI_AUDIO_DIR, greeting_audio)) > 0:
                db.execute(text("UPDATE ai_call_logs SET greeting_audio_url=:url WHERE id=:id"),
                           {"url": greeting_audio, "id": log_id})
                db.commit()
                greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{greeting_audio}</Play>'
                logger.info(f"[VOICE-SELECT] ✅ Returning caller log={log_id} saved={saved_agent}/{saved_lang}")
        except Exception as _e:
            logger.warning(f"[VOICE-SELECT] TTS failed for returning caller log={log_id}: {_e}")

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {greeting_block}
  </Gather>
  <Redirect method="POST">{respond_url}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # ── CAMPAIGN CALL or Non-Hindi: skip IVR, greet directly in campaign language ──
    # For ANY campaign call (campaign_id != 0), the language is already set by the campaign.
    # No IVR selection needed — go straight to the greeting in the chosen language.
    # IVR is only shown for standalone test/manual calls with no campaign where lang='hi'.
    if lang != "hi" or campaign_id != 0:
        direct_agent = preset_agent or "Vidya"
        direct_voice = preset_voice or "nova"
        twilio_lang  = LANG_MAP.get(lang, "hi-IN")

        # Commit language + agent into session
        db.execute(text("""
            UPDATE ai_call_sessions
            SET language = :lang, agent_voice = :voice, agent_name = :aname, updated_at = NOW()
            WHERE log_id = :lid
        """), {"lang": lang, "voice": direct_voice, "aname": direct_agent, "lid": log_id})
        db.commit()

        # Save language + agent preference to lead record (if linked to a real lead)
        db.execute(text("""
            UPDATE crm_leads
            SET ai_language = :lang, ai_preferred_agent = :agent, ai_preferred_voice = :voice
            WHERE id = (SELECT lead_id FROM ai_call_logs WHERE id = :lid)
              AND (SELECT lead_id FROM ai_call_logs WHERE id = :lid) IS NOT NULL
        """), {"lang": lang, "agent": direct_agent, "voice": direct_voice, "lid": log_id})
        db.commit()

        source_type = _get_lead_source_type(db, log_id)
        greeting = _build_greeting(direct_agent, lang, name, effective_segment, source_type)
        if not greeting:
            greeting = _build_greeting(direct_agent, "en", name, effective_segment, source_type)

        db.execute(text("""
            UPDATE ai_call_sessions
            SET conversation = :conv, updated_at = NOW()
            WHERE log_id = :lid
        """), {"conv": json.dumps([{"role": "assistant", "content": greeting}]), "lid": log_id})
        db.commit()

        respond_url = (
            f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
            f"?lang={lang}&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
        )

        safe_greeting = greeting.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        greeting_block = f'<Say voice="Polly.Aditi">{safe_greeting}</Say>'
        try:
            greeting_audio = await asyncio.wait_for(
                asyncio.to_thread(_generate_tts, greeting, lang, direct_voice),
                timeout=11.0,
            )
            if greeting_audio and os.path.exists(os.path.join(AI_AUDIO_DIR, greeting_audio)) \
                    and os.path.getsize(os.path.join(AI_AUDIO_DIR, greeting_audio)) > 0:
                db.execute(text("UPDATE ai_call_logs SET greeting_audio_url=:url WHERE id=:id"),
                           {"url": greeting_audio, "id": log_id})
                db.commit()
                greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{greeting_audio}</Play>'
                logger.info(f"[VOICE-SELECT] ✅ Pre-selected lang={lang} agent={direct_agent} log={log_id}")
        except Exception as _e:
            logger.warning(f"[VOICE-SELECT] Pre-selected TTS failed log={log_id}: {_e}")

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {greeting_block}
  </Gather>
  <Redirect method="POST">{respond_url}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # ── NEW CALLER (Hindi / unspecified): show language → agent selection IVR ──
    # Only reached when lang='hi' (no explicit pre-selection). The caller chooses
    # their language by speaking — existing flow is completely unchanged.
    lang_url = (
        f"{base}/api/v1/staff/ai-calling/webhook/lang-confirm"
        f"?log_id={log_id}&amp;name={_urlquote(name, safe='')}"
        f"&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
    )

    # Greeting + language choice prompt — accepts BOTH key press AND speech.
    # DTMF: 1=Hindi, 2=Telugu, 3=English (reliable; speech often fails in hi-IN mode).
    name_greeting = f" {name}!" if name else "!"
    lang_prompt = (
        f"Namaste{name_greeting} Welcome to Mynt Real LLP. "
        "Hindi ke liye 1 dabayein ya Hindi kahiye. "
        "Telugu ke liye 2 dabayein ya Telugu cheppandi. "
        "For English press 3 or say English."
    )

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech dtmf" action="{lang_url}" language="hi-IN"
          timeout="7" speechTimeout="auto" numDigits="1" method="POST">
    <Say voice="Polly.Aditi">{lang_prompt}</Say>
  </Gather>
  <Redirect method="POST">{lang_url}</Redirect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/lang-confirm")
async def webhook_lang_confirm(
    request: Request,
    log_id: int = Query(...),
    name: str = Query(""),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    STEP 2 — Language confirmation.
    Detects the caller's language choice, updates the session, then asks for
    agent selection (Vidya / Karthik) in the chosen language.
    All in one webhook — no redirect needed.
    """
    form_data = await request.form()
    speech    = form_data.get("SpeechResult", "").strip()
    digits    = form_data.get("Digits", "").strip()

    # DTMF takes priority: 1=Hindi, 2=Telugu, 3=English (reliable vs. hi-IN STT)
    _digit_map = {"1": "hi", "2": "te", "3": "en"}
    if digits and digits in _digit_map:
        detected_lang = _digit_map[digits]
        logger.info(f"[LANG-CONFIRM] DTMF={digits} → lang={detected_lang} log={log_id}")
    else:
        detected_lang = _detect_language(speech)
        logger.info(f"[LANG-CONFIRM] Speech={repr(speech)} → lang={detected_lang} log={log_id}")
    twilio_lang   = LANG_MAP.get(detected_lang, "hi-IN")

    # Persist detected language into session
    db.execute(text("""
        UPDATE ai_call_sessions
        SET language = :lang, updated_at = NOW()
        WHERE log_id = :lid
    """), {"lang": detected_lang, "lid": log_id})
    db.commit()

    base       = _webhook_base(request)
    # Use URL segment or fall back to campaign segment
    preset_agent, preset_voice, camp_segment = _get_campaign_persona(db, campaign_id)
    effective_segment = segment or camp_segment or ""
    seg_qs     = f"&amp;segment={_urlquote(effective_segment, safe='')}" if effective_segment else ""
    is_test_qs = f"&amp;is_test={is_test}" if is_test else ""

    # ── Campaign with PRESET AGENT: skip agent-selection prompt ─────────────────
    # If the campaign already has a configured agent (Karthik/Vidya), don't ask
    # the caller to choose — go straight to greeting with the preset agent.
    if preset_agent and preset_voice:
        # Update session with preset agent
        db.execute(text("""
            UPDATE ai_call_sessions
            SET agent_name = :aname, agent_voice = :voice, updated_at = NOW()
            WHERE log_id = :lid
        """), {"aname": preset_agent, "voice": preset_voice, "lid": log_id})
        db.commit()

        source_type = _get_lead_source_type(db, log_id)
        greeting = _build_greeting(preset_agent, detected_lang, name, effective_segment, source_type)
        if not greeting:
            greeting = _build_greeting(preset_agent, "en", name, effective_segment, source_type)

        db.execute(text("""
            UPDATE ai_call_sessions
            SET conversation = :conv, updated_at = NOW()
            WHERE log_id = :lid
        """), {"conv": json.dumps([{"role": "assistant", "content": greeting}]), "lid": log_id})
        db.commit()

        # Save language + agent preference to lead record
        db.execute(text("""
            UPDATE crm_leads
            SET ai_language = :lang, ai_preferred_agent = :agent, ai_preferred_voice = :voice
            WHERE id = (SELECT lead_id FROM ai_call_logs WHERE id = :lid)
              AND (SELECT lead_id FROM ai_call_logs WHERE id = :lid) IS NOT NULL
        """), {"lang": detected_lang, "agent": preset_agent, "voice": preset_voice, "lid": log_id})
        db.commit()

        respond_url = (
            f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
            f"?lang={detected_lang}&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
        )

        safe_greeting = greeting.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        greeting_block = f'<Say voice="Polly.Aditi">{safe_greeting}</Say>'
        try:
            greeting_audio = await asyncio.wait_for(
                asyncio.to_thread(_generate_tts, greeting, detected_lang, preset_voice),
                timeout=11.0,
            )
            if greeting_audio and os.path.exists(os.path.join(AI_AUDIO_DIR, greeting_audio)) \
                    and os.path.getsize(os.path.join(AI_AUDIO_DIR, greeting_audio)) > 0:
                db.execute(text("UPDATE ai_call_logs SET greeting_audio_url=:url WHERE id=:id"),
                           {"url": greeting_audio, "id": log_id})
                db.commit()
                greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{greeting_audio}</Play>'
                logger.info(f"[LANG-CONFIRM] ✅ Preset agent {preset_agent} log={log_id} lang={detected_lang}")
        except Exception as _e:
            logger.warning(f"[LANG-CONFIRM] TTS failed for preset agent log={log_id}: {_e}")

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {greeting_block}
  </Gather>
  <Redirect method="POST">{respond_url}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # ── No preset agent: show agent selection prompt ─────────────────────────────
    # voice-confirm URL now carries the DETECTED language
    confirm_url = (
        f"{base}/api/v1/staff/ai-calling/webhook/voice-confirm"
        f"?log_id={log_id}&amp;lang={detected_lang}&amp;name={_urlquote(name, safe='')}"
        f"&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
    )

    # Agent selection prompt in the detected language
    # DTMF: 1=Vidya (lady), 2=Karthik (male)
    AGENT_PROMPTS = {
        "hi": (
            "Dhanyavaad! Lady agent Vidya ke liye 1 dabayein ya Vidya kahiye. "
            "Male agent Karthik ke liye 2 dabayein ya Karthik kahiye."
        ),
        "te": (
            "Dhanyavaadalu! Lady agent Vidya kosam 1 press cheyandi ya Vidya cheppandi. "
            "Male agent Karthik kosam 2 press cheyandi ya Karthik cheppandi."
        ),
        "en": (
            "Thank you! Press 1 or say Vidya for our lady agent. "
            "Press 2 or say Karthik for our male agent."
        ),
    }
    agent_prompt = AGENT_PROMPTS[detected_lang]

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech dtmf" action="{confirm_url}" language="{twilio_lang}"
          timeout="7" speechTimeout="auto" numDigits="1" method="POST">
    <Say voice="Polly.Aditi">{agent_prompt}</Say>
  </Gather>
  <Redirect method="POST">{confirm_url}</Redirect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/voice-confirm")
async def webhook_voice_confirm(
    request: Request,
    log_id: int = Query(...),
    lang: str = Query("hi"),
    name: str = Query(""),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    Processes the customer's voice-choice (Vidya / Karthik), generates the
    greeting TTS inline, updates the session, and returns greeting + gather TwiML
    directly — NO redirect to /webhook/incoming needed.

    Design decision: merging confirm + greet into ONE webhook eliminates the
    <Redirect> step entirely, which was the root cause of "Application Error"
    (XML encoding issues with & in redirect URLs, plus an extra roundtrip).
    """
    form_data = await request.form()
    call_sid  = form_data.get("CallSid", "")
    speech    = form_data.get("SpeechResult", "").strip()
    digits    = form_data.get("Digits", "").strip()

    # DTMF takes priority: 1=Vidya (lady), 2=Karthik (male)
    if digits == "1":
        detected_agent, detected_voice = "Vidya", "nova"
        logger.info(f"[VOICE-CONFIRM] DTMF=1 → Vidya log={log_id}")
    elif digits == "2":
        detected_agent, detected_voice = "Karthik", "onyx"
        logger.info(f"[VOICE-CONFIRM] DTMF=2 → Karthik log={log_id}")
    else:
        detected_agent, detected_voice = _detect_voice_choice(speech)
    twilio_lang = LANG_MAP.get(lang, "hi-IN")

    # If caller gave no clear agent signal, fall back to what's already in the session
    # (pre-loaded from campaign preset in webhook_voice_select / lang-confirm)
    if detected_agent is None:
        sess_pre = db.execute(text(
            "SELECT agent_name, agent_voice FROM ai_call_sessions WHERE log_id=:lid"
        ), {"lid": log_id}).fetchone()
        agent_name = (sess_pre[0] if sess_pre and sess_pre[0] else None) or "Vidya"
        tts_voice  = (sess_pre[1] if sess_pre and sess_pre[1] else None) or "nova"
    else:
        agent_name = detected_agent
        tts_voice  = detected_voice

    # Use URL segment or fall back to campaign segment
    _, _, camp_segment = _get_campaign_persona(db, campaign_id)
    effective_segment = segment or camp_segment or ""

    # Build greeting — respect lead source so we don't say "enquiry ki thi" to reference/cold leads
    source_type = _get_lead_source_type(db, log_id)
    greeting    = _build_greeting(agent_name, lang, name, effective_segment, source_type)
    if not greeting:
        greeting = _build_greeting(agent_name, "en", name, effective_segment, source_type)

    # Save chosen agent into session + mark call connected
    db.execute(text("""
        UPDATE ai_call_sessions
        SET agent_voice = :voice, agent_name = :aname,
            conversation = :conv, updated_at = NOW()
        WHERE log_id = :lid
    """), {
        "voice": tts_voice, "aname": agent_name,
        "conv": json.dumps([{"role": "assistant", "content": greeting}]),
        "lid": log_id,
    })
    db.execute(text(
        "UPDATE ai_call_logs SET status='connected', call_sid=:sid WHERE id=:id"
    ), {"id": log_id, "sid": call_sid})
    # ── Save language + agent preference to the lead record for future calls ──
    # This lets us skip the selection prompts on repeat calls to the same contact.
    db.execute(text("""
        UPDATE crm_leads
        SET ai_language        = :lang,
            ai_preferred_agent = :agent,
            ai_preferred_voice = :voice
        WHERE id = (SELECT lead_id FROM ai_call_logs WHERE id = :lid)
          AND (SELECT lead_id FROM ai_call_logs WHERE id = :lid) IS NOT NULL
    """), {"lang": lang, "agent": agent_name, "voice": tts_voice, "lid": log_id})
    db.commit()

    base = _webhook_base(request)
    seg_qs     = f"&amp;segment={_urlquote(effective_segment, safe='')}" if effective_segment else ""
    is_test_qs = f"&amp;is_test={is_test}"                     if is_test else ""
    respond_url = (
        f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
        f"?lang={lang}&amp;campaign_id={campaign_id}{seg_qs}{is_test_qs}"
    )

    # Generate greeting TTS inline with the chosen voice (11s timeout → Polly fallback).
    # OpenAI TTS for a 30-word greeting typically takes 2-5s — well within Twilio's 15s budget.
    safe_greeting = greeting.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    greeting_block = f'<Say voice="Polly.Aditi">{safe_greeting}</Say>'
    try:
        greeting_audio = await asyncio.wait_for(
            asyncio.to_thread(_generate_tts, greeting, lang, tts_voice),
            timeout=11.0,
        )
        if greeting_audio and os.path.exists(os.path.join(AI_AUDIO_DIR, greeting_audio)) \
                and os.path.getsize(os.path.join(AI_AUDIO_DIR, greeting_audio)) > 0:
            db.execute(text(
                "UPDATE ai_call_logs SET greeting_audio_url=:url WHERE id=:id"
            ), {"url": greeting_audio, "id": log_id})
            db.commit()
            greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{greeting_audio}</Play>'
            logger.info(f"[VOICE-CONFIRM] ✅ Greeting ready log={log_id} agent={agent_name} voice={tts_voice} file={greeting_audio}")
    except Exception as _tts_err:
        logger.warning(f"[VOICE-CONFIRM] TTS failed log={log_id}: {_tts_err} — using Polly fallback")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {greeting_block}
  </Gather>
  <Redirect method="POST">{respond_url}</Redirect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


# ─────────────────────────────────────────────────────────
# TWILIO WEBHOOK — INCOMING CALL
# ─────────────────────────────────────────────────────────

@router.post("/webhook/incoming")
async def webhook_incoming(
    request: Request,
    log_id: int = Query(...),
    lang: str = Query("hi"),
    name: str = Query(""),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    Twilio calls this when the lead picks up.
    Returns TwiML immediately using a static greeting (no GPT/TTS here —
    avoids Twilio's 5-second webhook timeout). GPT kicks in from webhook_respond onwards.
    """
    # Read form data FIRST — must happen before any await/processing
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")

    twilio_lang = LANG_MAP.get(lang, "hi-IN")

    # Read agent choice set by voice-confirm (Vidya/nova or Karthik/onyx)
    sess_pre = db.execute(text(
        "SELECT agent_name, agent_voice FROM ai_call_sessions WHERE log_id=:lid"
    ), {"lid": log_id}).fetchone()
    incoming_agent_name  = (sess_pre[0] if sess_pre and sess_pre[0] else "Vidya") or "Vidya"
    incoming_agent_voice = (sess_pre[1] if sess_pre and sess_pre[1] else "nova")  or "nova"

    # Build greeting respecting lead source — don't say "enquiry ki thi" for reference/cold leads
    source_type = _get_lead_source_type(db, log_id)
    greeting = _build_greeting(incoming_agent_name, lang, name, segment, source_type)
    if not greeting:
        greeting = _build_greeting(incoming_agent_name, "en", name, segment, source_type)

    # Update status and save session — fast DB ops only
    db.execute(text(
        "UPDATE ai_call_logs SET status='connected', call_sid=:sid WHERE id=:id"
    ), {"id": log_id, "sid": call_sid})

    db.execute(text("""
        INSERT INTO ai_call_sessions
            (call_sid, campaign_id, log_id, lead_id, language, conversation, agent_voice, agent_name)
        SELECT :sid, NULLIF(:camp, 0), :lid, cl.lead_id, :lang, :conv, :voice, :aname
        FROM ai_call_logs cl WHERE cl.id = :lid
        ON CONFLICT (call_sid) DO UPDATE
            SET conversation = EXCLUDED.conversation
    """), {
        "sid": call_sid,
        "camp": campaign_id, "lid": log_id, "lang": lang,
        "conv": json.dumps([{"role": "assistant", "content": greeting}]),
        "voice": incoming_agent_voice, "aname": incoming_agent_name,
    })
    db.commit()

    base        = _webhook_base(request)
    respond_url = f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
    extra_qs    = f"&amp;segment={_urlquote(segment, safe='')}&amp;is_test={is_test}" if segment or is_test else ""

    # Use pre-generated greeting audio (from voice-confirm background task).
    # Falls back to inline TTS with the correct agent voice, or Polly as last resort.
    log_row = db.execute(
        text("SELECT greeting_audio_url FROM ai_call_logs WHERE id=:lid"), {"lid": log_id}
    ).fetchone()
    pre_greeting_audio = log_row[0] if log_row else None

    greeting_block = f'<Say voice="Polly.Aditi">{greeting}</Say>'  # final fallback
    if pre_greeting_audio and os.path.exists(os.path.join(AI_AUDIO_DIR, pre_greeting_audio)):
        # Pre-generated audio ready — zero wait, instant playback
        greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{pre_greeting_audio}</Play>'
    else:
        # Pre-gen not ready — generate now (5-10s, rare) using the chosen agent's voice
        try:
            greeting_audio = await asyncio.wait_for(
                asyncio.to_thread(_generate_tts, greeting, lang, incoming_agent_voice),
                timeout=12.0,
            )
            greeting_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{greeting_audio}</Play>'
        except Exception:
            pass  # keep Polly fallback

    # greeting_block is INSIDE <Gather> — customer can barge-in at any point.
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}?lang={lang}&amp;campaign_id={campaign_id}{extra_qs}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {greeting_block}
  </Gather>
  <Redirect method="POST">{respond_url}?lang={lang}&amp;campaign_id={campaign_id}{extra_qs}</Redirect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


def _get_campaign_company(db: Session, campaign_id: int) -> int:
    row = db.execute(text("SELECT company_id FROM ai_campaigns WHERE id=:id"), {"id": campaign_id}).fetchone()
    return row[0] if row else 4


@router.post("/webhook/respond/{log_id}")
async def webhook_respond(
    log_id: int,
    request: Request,
    lang: str = Query("hi"),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    db: Session = Depends(get_db),
):
    """
    Twilio calls this after the lead speaks (SpeechResult in form body).
    Returns IMMEDIATELY with a brief pause + redirect to /webhook/poll/{log_id}
    while GPT + TTS run in a background task. This avoids proxy/Twilio timeouts.
    """
    form         = await request.form()
    speech_result = form.get("SpeechResult", "").strip()
    twilio_lang  = LANG_MAP.get(lang, "hi-IN")

    session_row = db.execute(text(
        "SELECT conversation, language, agent_name, agent_voice FROM ai_call_sessions WHERE log_id=:lid"
    ), {"lid": log_id}).fetchone()

    conversation     = json.loads(session_row[0]) if session_row and session_row[0] else []
    # Use the session's saved language as the primary source of truth.
    # The URL ?lang= param is a fallback only — it might reflect the campaign default
    # rather than the language the caller actually chose during the selection flow.
    effective_lang   = (session_row[1] if session_row and session_row[1] else None) or lang
    twilio_lang      = LANG_MAP.get(effective_lang, "hi-IN")
    sess_agent_name  = (session_row[2] if session_row and session_row[2] else "Vidya") or "Vidya"
    sess_agent_voice = (session_row[3] if session_row and session_row[3] else "nova")  or "nova"

    if speech_result:
        conversation.append({"role": "user", "content": speech_result})
        # Auto-detect language from customer's Unicode script (Telugu / Hindi).
        # IMPORTANT: Do NOT downgrade from a regional language (te/hi) to 'en'.
        # 'en' is the default fallback when Twilio STT transcribes in Latin script
        # (common for Telugu speech via te-IN STT). We only switch when a DIFFERENT
        # regional language is clearly detected.
        detected = _detect_lang(speech_result)
        if detected != effective_lang and not (detected == "en" and effective_lang in ("te", "hi")):
            effective_lang = detected
            # Persist the switch so all subsequent turns use the new language
            try:
                db.execute(text(
                    "UPDATE ai_call_sessions SET language=:lang WHERE log_id=:lid"
                ), {"lang": effective_lang, "lid": log_id})
                db.commit()
            except Exception:
                pass

        # ── Explicit preference-change detection ─────────────────────────────
        # If the caller explicitly asks to switch language or agent mid-call,
        # update the session AND save the new preference to crm_leads so future
        # calls remember their updated choice automatically.
        pref_change = _detect_pref_change(speech_result)
        if pref_change:
            try:
                if pref_change[0] == "agent":
                    _, new_agent, new_voice = pref_change
                    sess_agent_name  = new_agent
                    sess_agent_voice = new_voice
                    db.execute(text("""
                        UPDATE ai_call_sessions
                        SET agent_name = :aname, agent_voice = :voice, updated_at = NOW()
                        WHERE log_id = :lid
                    """), {"aname": new_agent, "voice": new_voice, "lid": log_id})
                    # Persist to lead record
                    db.execute(text("""
                        UPDATE crm_leads
                        SET ai_preferred_agent = :agent, ai_preferred_voice = :voice
                        WHERE id = (SELECT lead_id FROM ai_call_logs WHERE id = :lid)
                          AND (SELECT lead_id FROM ai_call_logs WHERE id = :lid) IS NOT NULL
                    """), {"agent": new_agent, "voice": new_voice, "lid": log_id})
                    db.commit()
                    logger.info(f"[RESPOND] 🔄 Agent changed → {new_agent} log={log_id}")
                elif pref_change[0] == "lang":
                    _, new_lang = pref_change
                    effective_lang = new_lang
                    db.execute(text(
                        "UPDATE ai_call_sessions SET language=:lang WHERE log_id=:lid"
                    ), {"lang": new_lang, "lid": log_id})
                    # Persist to lead record
                    db.execute(text("""
                        UPDATE crm_leads
                        SET ai_language = :lang
                        WHERE id = (SELECT lead_id FROM ai_call_logs WHERE id = :lid)
                          AND (SELECT lead_id FROM ai_call_logs WHERE id = :lid) IS NOT NULL
                    """), {"lang": new_lang, "lid": log_id})
                    db.commit()
                    logger.info(f"[RESPOND] 🔄 Language changed → {new_lang} log={log_id}")
            except Exception as _pce:
                logger.warning(f"[RESPOND] Pref-change save failed log={log_id}: {_pce}")

    company_id    = _get_campaign_company(db, campaign_id)
    system_prompt = _build_system_prompt(
        db, company_id, effective_lang, segment=segment, is_test=bool(is_test),
        agent_name=sess_agent_name,
    )

    if not speech_result:
        # No speech — no-input fast path: respond inline (no GPT needed, tiny latency)
        # Use effective_lang (from session) — NOT url-param lang which may be stale
        silence_reply = (
            "క్షమించండి, మీ మాటలు వినలేకపోయాను. దయచేసి మళ్ళీ చెప్పగలరా?"
            if effective_lang == "te" else
            "Sorry, I couldn't hear you. Could you please repeat?"
            if effective_lang == "en" else
            "क्षमा करें, मुझे आपकी बात सुनाई नहीं दी। क्या आप फिर से बोल सकते हैं?"
        )
        respond_url  = f"{_webhook_base(request)}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
        extra_qs     = f"&amp;segment={_urlquote(segment, safe='')}&amp;is_test={is_test}" if segment or is_test else ""
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}?lang={effective_lang}&amp;campaign_id={campaign_id}{extra_qs}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    <Say voice="Polly.Aditi">{silence_reply}</Say>
  </Gather>
  <Redirect method="POST">{respond_url}?lang={effective_lang}&amp;campaign_id={campaign_id}{extra_qs}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # Mark session as processing so the poll endpoint can distinguish states.
    # Use upsert in case webhook_incoming session insert hasn't committed yet.
    form_call_sid = form.get("CallSid", "")
    db.execute(text("""
        INSERT INTO ai_call_sessions (call_sid, log_id, campaign_id, language, conversation, next_audio_url)
        VALUES (:sid, :lid, NULLIF(:camp,0), :lang, :conv, 'PROCESSING')
        ON CONFLICT (call_sid) DO UPDATE
            SET next_audio_url = 'PROCESSING',
                next_reply_text = NULL,
                conversation    = EXCLUDED.conversation,
                updated_at      = NOW()
    """), {
        "sid":  form_call_sid or f"_ncs_{log_id}",
        "lid":  log_id, "camp": campaign_id, "lang": effective_lang,
        "conv": json.dumps(conversation),
    })
    db.execute(text(
        "UPDATE ai_call_logs SET transcript=:trans WHERE id=:id"
    ), {"trans": json.dumps(conversation), "id": log_id})
    db.commit()

    # Fire GPT + TTS in background (will write result back to ai_call_sessions.next_audio_url)
    asyncio.create_task(_bg_gpt_tts(log_id, conversation, system_prompt, effective_lang))
    # Kick off filler generation for this language in background (no-op if already cached)
    asyncio.create_task(asyncio.to_thread(_ensure_fillers_sync, effective_lang))

    # Return immediately — play a filler phrase so the customer stays engaged,
    # then redirect to poll once GPT+TTS is ready.
    base     = _webhook_base(request)
    poll_url = (
        f"{base}/api/v1/staff/ai-calling/webhook/poll/{log_id}"
        f"?lang={effective_lang}&amp;campaign_id={campaign_id}"
    )
    if segment:
        poll_url += f"&amp;segment={_urlquote(segment, safe='')}"
    if is_test:
        poll_url += f"&amp;is_test={is_test}"

    # ── Filler: audio fillers are Vidya-voice only — use <Say> for Karthik ──────
    _filler_say_map = {
        "hi": ("Haan ji, ek pal mein batata hoon..." if sess_agent_voice != "nova"
               else "Haan ji, ek pal mein batati hoon..."),
        "te": "Avunu, okka nimisham...",
        "en": "Sure, just a moment...",
    }
    filler_files = _FILLER_CACHE.get(effective_lang, []) if sess_agent_voice == "nova" else []
    if filler_files:
        filler_fname = _random.choice(filler_files)
        filler_block = f'<Play>{base}/api/v1/staff/ai-calling/audio/{filler_fname}</Play>'
        pause_sec    = 1   # filler already fills ~2s; short extra pause before poll
    else:
        _filler_say  = _filler_say_map.get(effective_lang, "Just a moment...")
        filler_block = f'<Say voice="Polly.Aditi">{_filler_say}</Say>'
        pause_sec    = 2

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  {filler_block}
  <Pause length="{pause_sec}"/>
  <Redirect method="POST">{poll_url}&amp;attempt=1</Redirect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/poll/{log_id}")
async def webhook_poll(
    log_id: int,
    request: Request,
    lang: str = Query("hi"),
    campaign_id: int = Query(0),
    segment: str = Query(""),
    is_test: int = Query(0),
    attempt: int = Query(1),
    db: Session = Depends(get_db),
):
    """
    Polling endpoint called by Twilio after the pause in webhook_respond.
    Checks if the background GPT+TTS task has finished. If ready, plays the audio
    and presents the next Gather. If not ready, adds another short pause + redirect.
    """
    MAX_POLLS = 10  # 10 × 3s = 30s max wait
    twilio_lang = LANG_MAP.get(lang, "hi-IN")
    base        = _webhook_base(request)
    respond_url = f"{base}/api/v1/staff/ai-calling/webhook/respond/{log_id}"
    poll_url    = f"{base}/api/v1/staff/ai-calling/webhook/poll/{log_id}"
    extra_qs    = (
        f"?lang={lang}&amp;campaign_id={campaign_id}"
        + (f"&amp;segment={_urlquote(segment, safe='')}" if segment else "")
        + (f"&amp;is_test={is_test}" if is_test else "")
    )

    row = db.execute(text(
        "SELECT next_audio_url, next_reply_text, status FROM ai_call_sessions WHERE log_id=:lid"
    ), {"lid": log_id}).fetchone()

    audio_url_val = row[0] if row else None
    reply_text    = row[1] if row else ""
    sess_status   = row[2] if row else "active"

    # ── Case A: still processing → poll again
    if audio_url_val in (None, "PROCESSING"):
        if attempt >= MAX_POLLS:
            # Fallback: use Twilio <Say> inline
            fallback = (
                "एक क्षण रुकिए, मैं आपकी बात समझ रहा हूं।"
                if lang == "hi" else
                "ఒక్క నిమిషం, మీ మాటలు అర్థం చేసుకుంటున్నాను."
                if lang == "te" else
                "One moment, I'm processing your response."
            )
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}{extra_qs}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    <Say voice="Polly.Aditi">{fallback}</Say>
  </Gather>
  <Redirect method="POST">{respond_url}{extra_qs}</Redirect>
</Response>"""
        else:
            next_poll = f"{poll_url}{extra_qs}&amp;attempt={attempt + 1}"
            # Always use a short pause in poll — filler was already played
            # in webhook_respond so the customer has already heard one.
            # Playing another here causes the "multiple fillers" problem.
            twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Pause length="1"/>
  <Redirect method="POST">{next_poll}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # ── Case B: error → fallback Say + continue
    if audio_url_val == "ERROR":
        db.execute(text(
            "UPDATE ai_call_sessions SET next_audio_url=NULL, next_reply_text=NULL WHERE log_id=:lid"
        ), {"lid": log_id})
        db.commit()
        err_msg = (
            "क्षमा करें, कोई तकनीकी समस्या आई। क्या आप अपनी बात दोहरा सकते हैं?"
            if lang == "hi" else
            "క్షమించండి, సాంకేతిక సమస్య వచ్చింది. దయచేసి మళ్ళీ చెప్పగలరా?"
            if lang == "te" else
            "Sorry, a technical issue occurred. Could you please repeat?"
        )
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}{extra_qs}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    <Say voice="Polly.Aditi">{err_msg}</Say>
  </Gather>
  <Redirect method="POST">{respond_url}{extra_qs}</Redirect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")

    # ── Case C: audio URL is set — verify file actually exists on disk
    # (Background TTS task may have written the URL to DB but the file write
    #  may not be flushed yet — especially under multi-worker race conditions.)
    if audio_url_val not in (None, "PROCESSING", "ERROR", "FALLBACK"):
        audio_disk_path = os.path.join(AI_AUDIO_DIR, os.path.basename(audio_url_val))
        if not os.path.exists(audio_disk_path):
            # File not on disk yet — treat as still PROCESSING (poll again)
            if attempt >= MAX_POLLS:
                pass  # fall through to FALLBACK below
            else:
                next_poll = f"{poll_url}{extra_qs}&amp;attempt={attempt + 1}"
                twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Pause length="2"/>
  <Redirect method="POST">{next_poll}</Redirect>
</Response>"""
                return Response(content=twiml, media_type="application/xml")

    # ── Consume and play
    db.execute(text(
        "UPDATE ai_call_sessions SET next_audio_url=NULL, next_reply_text=NULL WHERE log_id=:lid"
    ), {"lid": log_id})
    db.commit()

    # Check if call should end (status set by _bg_gpt_tts)
    should_hangup  = sess_status in ("end_call_pending", "callback_pending")
    call_outcome   = "callback" if sess_status == "callback_pending" else "qualified"

    if should_hangup:
        conv_row = db.execute(text(
            "SELECT conversation FROM ai_call_sessions WHERE log_id=:lid"
        ), {"lid": log_id}).fetchone()
        conv = json.loads(conv_row[0]) if conv_row and conv_row[0] else []
        _finalize_call(db, log_id, call_outcome, conv, lang, campaign_id)

    # Build play block
    if audio_url_val == "FALLBACK" or not audio_url_val:
        play_block = f'<Say voice="Polly.Aditi">{reply_text or "Thank you for speaking with us."}</Say>'
    else:
        audio_serve_url = f"{base}/api/v1/staff/ai-calling/audio/{audio_url_val}"
        play_block = f'<Play>{audio_serve_url}</Play>'

    if should_hangup:
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  {play_block}
  <Pause length="1"/>
  <Hangup/>
</Response>"""
    else:
        # play_block is INSIDE <Gather> so the customer can barge-in (interrupt Vidya)
        # at any point. Twilio stops audio immediately when speech is detected.
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather input="speech" action="{respond_url}{extra_qs}"
          language="{twilio_lang}" timeout="8" speechTimeout="auto" method="POST">
    {play_block}
  </Gather>
  <Redirect method="POST">{respond_url}{extra_qs}</Redirect>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/recording")
async def webhook_recording(
    request: Request,
    log_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """
    Twilio posts here when a call recording is ready.
    Stores the recording URL in ai_call_logs.recording_url.
    """
    form          = await request.form()
    recording_url = form.get("RecordingUrl", "")
    recording_sid = form.get("RecordingSid", "")
    call_sid      = form.get("CallSid", "")

    if recording_url:
        # Append .mp3 so it streams directly in browser
        if not recording_url.endswith(".mp3"):
            recording_url = recording_url + ".mp3"

        if log_id:
            db.execute(text(
                "UPDATE ai_call_logs SET recording_url=:url WHERE id=:id"
            ), {"url": recording_url, "id": log_id})
        else:
            # Fall back to CallSid lookup
            db.execute(text(
                "UPDATE ai_call_logs SET recording_url=:url WHERE call_sid=:sid"
            ), {"url": recording_url, "sid": call_sid})
        db.commit()
        logger.info(f"[AI_CALLING] Recording stored for log {log_id}: {recording_sid}")

    return Response(content="<?xml version='1.0'?><Response/>", media_type="application/xml")


@router.get("/recording-proxy/{log_id}")
async def proxy_recording(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Stream Twilio recording through backend with auth so browser can play it."""
    import httpx as _httpx
    row = db.execute(text(
        "SELECT recording_url FROM ai_call_logs WHERE id=:id AND company_id=:cid"
    ), {"id": log_id, "cid": current_user.base_company_id}).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Recording not found")
    rec_url = row[0]
    try:
        r = _httpx.get(rec_url, auth=(TWILIO_SID, TWILIO_TOKEN), timeout=20, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch recording: {e}")
    from starlette.responses import StreamingResponse
    return StreamingResponse(
        iter([r.content]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="call_{log_id}.mp3"',
                 "Content-Length": str(len(r.content))},
    )


# ─────────────────────────────────────────────────────────
# RECORDING SHARE — 3-hour expirable public links
# ─────────────────────────────────────────────────────────

@router.post("/recording-share/{log_id}")
async def create_recording_share(
    log_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Generate a 3-hour expirable public link for a call recording."""
    import secrets as _secrets
    from datetime import timezone

    row = db.execute(text(
        "SELECT recording_url, started_at, duration_seconds, language_used FROM ai_call_logs WHERE id=:id AND company_id=:cid"
    ), {"id": log_id, "cid": current_user.base_company_id}).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Recording not found")

    token = _secrets.token_urlsafe(32)
    expires_at = get_ist_now() + timedelta(hours=3)

    db.execute(text("""
        INSERT INTO ai_recording_share_tokens (token, log_id, created_by, expires_at)
        VALUES (:tok, :lid, :uid, :exp)
        ON CONFLICT (token) DO NOTHING
    """), {"tok": token, "lid": log_id, "uid": current_user.id, "exp": expires_at})
    db.commit()

    base = _webhook_base(request)
    share_url = f"{base}/api/v1/staff/ai-calling/recording-share/play/{token}"
    return {"success": True, "share_url": share_url, "expires_at": expires_at.isoformat(), "token": token}


@router.get("/recording-share/play/{token}")
async def play_shared_recording(token: str, db: Session = Depends(get_db)):
    """Public endpoint (no auth) — serves standalone HTML player for shared recording."""
    from fastapi.responses import HTMLResponse
    now = get_ist_now()

    row = db.execute(text("""
        SELECT t.log_id, t.expires_at, l.recording_url, l.started_at, l.duration_seconds, l.language_used,
               cl.name as lead_name, s.agent_name
        FROM ai_recording_share_tokens t
        JOIN ai_call_logs l ON l.id = t.log_id
        LEFT JOIN crm_leads cl ON cl.id = l.lead_id
        LEFT JOIN ai_call_sessions s ON s.log_id = l.id
        WHERE t.token = :tok
    """), {"tok": token}).fetchone()

    if not row:
        return HTMLResponse(_share_error_page("Link not found", "This share link is invalid or has been removed."), status_code=404)

    expires_at = row[1]
    if now > expires_at:
        return HTMLResponse(_share_error_page("Link Expired", "This recording link has expired. Links are valid for 3 hours only."), status_code=410)

    log_id       = row[0]
    started_at   = row[3]
    duration_sec = row[4] or 0
    language     = row[5] or "hi"
    lead_name    = row[6] or "Customer"
    _raw_agent   = (row[7] or "Vidya").strip()
    agent_label  = f"VGK {_raw_agent}" if _raw_agent in ("Vidya", "Karthik") else _raw_agent
    lang_label   = {"hi": "Hindi", "te": "Telugu", "en": "English"}.get(language, language.upper())

    mins_left    = int((expires_at - now).total_seconds() / 60)
    dur_str      = f"{duration_sec // 60}m {duration_sec % 60}s" if duration_sec else "—"
    date_str     = started_at.strftime("%d %b %Y, %I:%M %p IST") if started_at else "—"
    audio_url    = f"/api/v1/staff/ai-calling/recording-share/audio/{token}"
    expiry_str   = expires_at.strftime("%I:%M %p IST")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Call Recording — Mynt Real LLP</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
  .card{{background:#1e293b;border-radius:16px;padding:32px;max-width:480px;width:100%;box-shadow:0 25px 60px rgba(0,0,0,.5)}}
  .logo{{display:flex;align-items:center;gap:10px;margin-bottom:24px}}
  .logo-icon{{width:40px;height:40px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}}
  .logo-text{{font-size:15px;font-weight:700;color:#f1f5f9}}
  .logo-sub{{font-size:11px;color:#64748b}}
  h2{{font-size:18px;font-weight:600;color:#f1f5f9;margin-bottom:6px}}
  .subtitle{{font-size:13px;color:#94a3b8;margin-bottom:24px}}
  .meta-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:24px}}
  .meta-item{{background:#0f172a;border-radius:10px;padding:12px}}
  .meta-label{{font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}}
  .meta-value{{font-size:13px;font-weight:600;color:#e2e8f0}}
  .player-wrap{{background:#0f172a;border-radius:12px;padding:20px;margin-bottom:20px}}
  audio{{width:100%;outline:none;border-radius:8px}}
  .expiry{{display:flex;align-items:center;gap:8px;padding:10px 14px;border-radius:8px;font-size:12px}}
  .expiry.ok{{background:#052e16;color:#4ade80;border:1px solid #166534}}
  .expiry.warn{{background:#431407;color:#fb923c;border:1px solid #9a3412}}
  .expiry-icon{{font-size:14px}}
  .footer{{margin-top:20px;text-align:center;font-size:11px;color:#334155}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <div class="logo-icon">🏠</div>
    <div>
      <div class="logo-text">Mynt Real LLP</div>
      <div class="logo-sub">AI Call Recording</div>
    </div>
  </div>
  <h2>Call Recording</h2>
  <p class="subtitle">Shared by Mynt Real LLP · AI Consultant {agent_label}</p>
  <div class="meta-grid">
    <div class="meta-item">
      <div class="meta-label">Customer</div>
      <div class="meta-value">{lead_name}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Language</div>
      <div class="meta-value">{lang_label}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Date &amp; Time</div>
      <div class="meta-value" style="font-size:11px">{date_str}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Duration</div>
      <div class="meta-value">{dur_str}</div>
    </div>
  </div>
  <div class="player-wrap">
    <audio controls autoplay>
      <source src="{audio_url}" type="audio/mpeg">
      Your browser does not support audio playback.
    </audio>
  </div>
  <div class="expiry {'warn' if mins_left < 30 else 'ok'}">
    <span class="expiry-icon">{'⚠️' if mins_left < 30 else '🔒'}</span>
    <span>This link expires at <strong>{expiry_str}</strong> ({mins_left} min remaining)</span>
  </div>
  <div class="footer">This recording is confidential. Do not share further.</div>
</div>
</body>
</html>"""
    return HTMLResponse(html)


@router.get("/recording-share/audio/{token}")
async def stream_shared_audio(token: str, db: Session = Depends(get_db)):
    """Public endpoint — streams the actual audio bytes for a valid share token."""
    import httpx as _httpx
    now = get_ist_now()

    row = db.execute(text("""
        SELECT t.expires_at, l.recording_url
        FROM ai_recording_share_tokens t
        JOIN ai_call_logs l ON l.id = t.log_id
        WHERE t.token = :tok
    """), {"tok": token}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Invalid share token")
    if now > row[0]:
        raise HTTPException(status_code=410, detail="Share link has expired")
    if not row[1]:
        raise HTTPException(status_code=404, detail="Recording not available")

    try:
        r = _httpx.get(row[1], auth=(TWILIO_SID, TWILIO_TOKEN), timeout=20, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch recording: {e}")

    from starlette.responses import StreamingResponse
    return StreamingResponse(
        iter([r.content]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'inline; filename="recording.mp3"',
                 "Content-Length": str(len(r.content))},
    )


def _share_error_page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title} — Mynt Real LLP</title>
<style>
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
  .card{{background:#1e293b;border-radius:16px;padding:40px;max-width:400px;width:100%;text-align:center}}
  .icon{{font-size:48px;margin-bottom:16px}}
  h2{{color:#f1f5f9;font-size:20px;margin-bottom:10px}}
  p{{color:#94a3b8;font-size:14px;line-height:1.6}}
  .brand{{margin-top:24px;font-size:11px;color:#334155}}
</style>
</head>
<body>
<div class="card">
  <div class="icon">🔒</div>
  <h2>{title}</h2>
  <p>{message}</p>
  <div class="brand">Mynt Real LLP · AI Calling System</div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────
# BROCHURE UPLOAD + AI EXTRACTION
# ─────────────────────────────────────────────────────────

@router.post("/brochure-extract")
async def brochure_extract(
    request: Request,
    segment: str = Query(""),
    save: int = Query(0),   # kept for backwards-compat but ignored — always auto-saves
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Upload a PDF/image brochure → extract ALL text → AI enrichment → auto-save to KB.
    Always auto-saves using _ai_enrich_and_save (creates multiple well-structured entries).
    """
    import tempfile, httpx as _httpx

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    filename = getattr(file, "filename", "upload.pdf").lower()
    content  = await file.read()

    # ── Extract text ──
    raw_text = ""
    if filename.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            # Use pymupdf (fitz) — robust, no pdfminer dependency issues
            import fitz  # pymupdf
            with fitz.open(tmp_path) as doc:
                for page in doc:
                    try:
                        t = page.get_text()
                        if t:
                            raw_text += t + "\n"
                    except Exception:
                        pass
        except Exception:
            # Final fallback: try pypdf
            try:
                import pypdf
                with open(tmp_path, "rb") as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        try:
                            t = page.extract_text()
                            if t:
                                raw_text += t + "\n"
                        except Exception:
                            pass
            except Exception:
                pass
        finally:
            os.remove(tmp_path)

    elif filename.endswith((".txt", ".text", ".md")):
        # Plain text / markdown — read directly
        try:
            raw_text = content.decode("utf-8", errors="replace")
        except Exception:
            raw_text = content.decode("latin-1", errors="replace")

    elif filename.endswith((".docx", ".doc")):
        # Word document — extract paragraphs via python-docx
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            import docx as _docx
            doc = _docx.Document(tmp_path)
            raw_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            raw_text = ""
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    elif filename.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
        # Image — send to GPT-4o vision
        import base64
        b64 = base64.b64encode(content).decode()
        if filename.endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"
        elif filename.endswith(".webp"):
            mime = "image/webp"
        elif filename.endswith(".gif"):
            mime = "image/gif"
        else:
            mime = "image/png"
        vision_payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": [
                {"type": "text",  "text": "Extract all text from this real estate brochure. Return everything verbatim."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]}],
            "max_tokens": 2000,
        }
        vr = _httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json=vision_payload, timeout=40,
        )
        vr.raise_for_status()
        raw_text = vr.json()["choices"][0]["message"]["content"]

    else:
        # Unknown type — try UTF-8 decode as last resort
        try:
            raw_text = content.decode("utf-8", errors="replace")
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}. Supported: PDF, DOCX, TXT, JPG, PNG."
            )

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file")

    seg_name = (segment or "General").strip()
    raw_chars = len(raw_text)

    # ── AI Enrichment: extract all knowledge and save to KB automatically ──
    # Use the full enrichment pipeline — creates multiple well-structured, searchable
    # KB entries per topic (pricing, USPs, location, legal, etc.) and saves them all.
    # This replaces the old "structured JSON → manual save" approach.
    saved_entries = _ai_enrich_and_save(
        company_id=current_user.base_company_id,
        raw_input=raw_text[:8000],   # up to 8 k chars — covers most brochures fully
        question=None,
        creator=current_user.emp_code,
        db=db,
        context_segment=seg_name,
    )

    # ── Contradiction detection (informational only — save already happened) ──
    conflicts = []
    try:
        if saved_entries and OPENAI_KEY:
            existing_rows = db.execute(text("""
                SELECT title, content, category FROM ai_product_catalogue
                WHERE company_id=:cid AND segment=:seg AND is_active=TRUE
                  AND id NOT IN :new_ids
                LIMIT 30
            """), {
                "cid": current_user.base_company_id,
                "seg": seg_name,
                "new_ids": tuple(e["id"] for e in saved_entries) or (0,),
            }).fetchall()

            if existing_rows:
                existing_text = "\n".join(
                    f"- [{r[2]}] {r[0]}: {r[1][:120]}" for r in existing_rows
                )
                new_text = "\n".join(
                    f"- [{e.get('category','')}] {e.get('title','')}: {e.get('content','')[:120]}"
                    for e in saved_entries
                )
                conflict_prompt = f"""You are checking for contradictions between existing and newly uploaded knowledge base data.

EXISTING:
{existing_text}

NEW (just uploaded):
{new_text}

Identify ONLY genuine contradictions (e.g. different prices, conflicting specs).
Ignore additive info. Return JSON array: [{{"field":"","existing":"","new":"","recommendation":"use_new|keep_existing|verify"}}]
If none, return []. ONLY valid JSON."""

                import httpx as _hx2
                cr = _hx2.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini",
                          "messages": [{"role": "user", "content": conflict_prompt}],
                          "max_tokens": 400, "temperature": 0.1},
                    timeout=20,
                )
                cr.raise_for_status()
                raw_conflicts = cr.json()["choices"][0]["message"]["content"].strip()
                if raw_conflicts.startswith("```"):
                    raw_conflicts = raw_conflicts.split("```")[1]
                    if raw_conflicts.startswith("json"):
                        raw_conflicts = raw_conflicts[4:]
                conflicts = json.loads(raw_conflicts.strip())
                if not isinstance(conflicts, list):
                    conflicts = []
    except Exception as ce:
        logger.warning(f"[BROCHURE] Contradiction check failed: {ce}")
        conflicts = []

    return {
        "success": True,
        "segment": seg_name,
        "entries": saved_entries,          # already saved
        "entries_saved": len(saved_entries),
        "raw_chars": raw_chars,
        "conflicts": conflicts,
        "auto_saved": True,
    }


@router.get("/segments-overview")
def segments_overview(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """All segments for this company with entry counts and sample entries."""
    rows = db.execute(text("""
        SELECT segment,
               COUNT(*) AS total,
               COUNT(*) FILTER (WHERE is_active) AS active,
               MAX(created_at) AS last_updated
        FROM ai_product_catalogue
        WHERE company_id = :cid
        GROUP BY segment
        ORDER BY segment
    """), {"cid": current_user.base_company_id}).fetchall()

    segments = [
        {"name": r[0], "total": r[1], "active": r[2],
         "last_updated": r[3].isoformat() if r[3] else None}
        for r in rows
    ]
    return {"success": True, "segments": segments}


# ─────────────────────────────────────────────────────────────
# KNOWLEDGE VOICE CHAT — staff ask questions, Vidya answers in voice
# ─────────────────────────────────────────────────────────────

@router.post("/knowledge-chat")
async def knowledge_chat(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """
    Staff ask a question about the knowledge base; Vidya answers in text + voice.
    segment='' means all segments.  language controls TTS voice.
    """
    question = (payload.get("question") or "").strip()
    segment  = (payload.get("segment") or "").strip()
    language = payload.get("language", "en")
    want_voice = payload.get("voice", True)

    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if not OPENAI_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    # ── Pull catalogue knowledge ──
    q_sql = """
        SELECT segment, category, title, content
        FROM ai_product_catalogue
        WHERE company_id = :cid AND is_active = TRUE
    """
    params: dict = {"cid": current_user.base_company_id}
    if segment:
        q_sql += " AND segment = :seg"
        params["seg"] = segment
    q_sql += " ORDER BY segment, category, sort_order"
    rows = db.execute(text(q_sql), params).fetchall()

    if rows:
        catalogue_text = "\n".join(
            f"[{r[0]}] {r[1]} — {r[2]}: {r[3]}" for r in rows
        )
    else:
        catalogue_text = "No knowledge base entries found for this segment."

    lang_label = {"hi": "Hindi", "te": "Telugu", "en": "English"}.get(language, "English")
    scope_note = f"for the '{segment}' project" if segment else "across all projects"

    system_prompt = (
        f"You are a knowledgeable real estate assistant at Mynt Real LLP, answering "
        f"questions from internal staff {scope_note}.\n"
        f"Reply concisely in {lang_label} — keep answers under 4 sentences because "
        f"the response will be spoken aloud by text-to-speech.\n"
        f"If the information is not in the knowledge base below, say so honestly.\n\n"
        f"KNOWLEDGE BASE:\n{catalogue_text}"
    )

    import httpx as _httpx

    gpt_payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question},
        ],
        "max_tokens": 250,
        "temperature": 0.65,
    }
    try:
        resp = _httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json=gpt_payload,
            timeout=30,
        )
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GPT error: {exc}")

    # ── TTS — run in executor so we don't block the event loop ──
    audio_url: Optional[str] = None
    if want_voice:
        try:
            loop = __import__("asyncio").get_event_loop()
            audio_file = await loop.run_in_executor(None, lambda: _generate_tts(answer, language))
            audio_url = f"/api/v1/staff/ai-calling/audio/{audio_file}"
        except Exception:
            pass   # voice failure is non-fatal — we still return the text answer

    return {"success": True, "answer": answer, "audio_url": audio_url}


@router.post("/webhook/status")
async def webhook_status(
    request: Request,
    log_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Twilio fires this on call completion."""
    form        = await request.form()
    call_status = form.get("CallStatus", "completed")
    duration    = int(form.get("CallDuration", 0) or 0)

    status_map = {
        "completed": "completed", "failed": "failed",
        "busy": "busy", "no-answer": "no_answer",
        "canceled": "canceled",
    }
    final_status = status_map.get(call_status, "completed")

    log_row = db.execute(text(
        "SELECT transcript, language_used, campaign_id, lead_id, attempt_number FROM ai_call_logs WHERE id=:id"
    ), {"id": log_id}).fetchone()

    transcript, lang, campaign_id, lead_id, attempt_number = [], "hi", 0, 0, 1
    if log_row:
        try:
            transcript = json.loads(log_row[0] or "[]")
        except Exception:
            transcript = []
        lang           = log_row[1] or "hi"
        campaign_id    = log_row[2] or 0
        lead_id        = log_row[3] or 0
        attempt_number = log_row[4] or 1

    # Always run GPT analysis if there's a transcript (even on disconnect/busy)
    # so we can extract lead details regardless of call outcome.
    analysis: dict = {}
    if transcript:
        try:
            analysis      = _gpt_summarize(transcript, lang)
            outcome       = analysis.get("outcome", "no_answer")
            summary       = analysis.get("summary", "")
            detected_lang = analysis.get("detected_language", lang)
        except Exception as _se:
            logger.warning(f"[STATUS] GPT summarize failed log={log_id}: {_se}")
            outcome = "no_answer" if final_status in ("no_answer","busy","failed","canceled") else "completed"
            summary = ""
            detected_lang = lang
    else:
        outcome = "no_answer" if final_status in ("no_answer","busy","failed","canceled") else "completed"
        summary = ""
        detected_lang = lang

    # Compute retry time for failed/missed calls
    next_retry_at = None
    if final_status in ("no_answer", "busy", "failed", "canceled") and campaign_id:
        try:
            retry_cfg = db.execute(text(
                "SELECT retry_1_hours, retry_2_hours, retry_day2_offset, retry_day10_offset"
                " FROM ai_campaigns WHERE id=:id"
            ), {"id": campaign_id}).fetchone()
            if retry_cfg:
                r1h, r2h, rd2, rd10 = retry_cfg
                if attempt_number == 1:
                    next_retry_at = datetime.utcnow() + timedelta(hours=int(r1h or 2))
                elif attempt_number == 2:
                    next_retry_at = datetime.utcnow() + timedelta(hours=int(r2h or 4))
                elif attempt_number == 3:
                    next_retry_at = datetime.utcnow() + timedelta(days=int(rd2 or 2))
                elif attempt_number == 4:
                    next_retry_at = datetime.utcnow() + timedelta(days=int(rd10 or 10))
                # attempt_number >= 5: no more scheduled retries
        except Exception as retry_err:
            logger.warning(f"[AI_CALLING] Could not compute retry time: {retry_err}")

    db.execute(text("""
        UPDATE ai_call_logs
        SET status=:status, duration_seconds=:dur, outcome=:outcome,
            ai_summary=:summary, ended_at=NOW(), next_retry_at=:retry_at
        WHERE id=:id
    """), {"status": final_status, "dur": duration, "outcome": outcome or "no_answer",
           "summary": summary, "id": log_id, "retry_at": next_retry_at})

    # ── Full CRM lead update with every extracted detail ───────────────────────
    # Parse numerics safely
    def _to_float(v):
        try:
            return float(str(v).replace(",", "").replace("₹","").replace("L","00000").replace("K","000"))
        except Exception:
            return None

    # Helper: fetch agent name from session (Vidya / Karthik)
    def _get_agent_name_for_log(log_id_: int) -> str:
        try:
            row = db.execute(text(
                "SELECT s.agent_name FROM ai_call_sessions s WHERE s.log_id = :lid LIMIT 1"
            ), {"lid": log_id_}).fetchone()
            return row[0] if row and row[0] else "AI Assistant"
        except Exception:
            return "AI Assistant"

    # Helper: insert a remark into crm_lead_notes attributed to the AI agent
    def _write_ai_call_note(target_lead_id: int, agent: str,
                             note_outcome: str, note_summary: str,
                             status_before: Optional[str], status_after: Optional[str],
                             note_lang: str, note_duration: int,
                             note_followup, note_rich: Optional[str]) -> None:
        try:
            LANG_LABELS = {"hi": "Hindi", "te": "Telugu", "en": "English"}
            OUTCOME_LABELS = {
                "interested": "Interested", "qualified": "Qualified",
                "callback": "Callback Requested", "connected": "Connected",
                "in_progress": "In Progress", "not_interested": "Not Interested",
                "no_answer": "No Answer", "busy": "Busy",
                "failed": "Failed", "canceled": "Canceled",
            }
            dur_str = (f"{note_duration//60}m {note_duration%60}s"
                       if note_duration and note_duration >= 60 else f"{note_duration or 0}s")
            lang_str = LANG_LABELS.get(note_lang, note_lang.upper())
            outcome_str = OUTCOME_LABELS.get(note_outcome or "", note_outcome or "No Answer")

            status_line = ""
            if status_before and status_after:
                if status_before != status_after:
                    status_line = f"\n🔄 CRM Status: {status_before} → {status_after}"
                else:
                    status_line = f"\n📌 CRM Status: {status_before} (unchanged)"

            note_lines = [
                f"📞 AI Call by {agent}",
                f"Outcome: {outcome_str}  |  Language: {lang_str}  |  Duration: {dur_str}",
                status_line,
            ]
            if note_summary:
                note_lines.append(f"\n📝 Summary: {note_summary}")
            if note_rich:
                note_lines.append(f"💡 Key Info: {note_rich}")
            if note_followup:
                note_lines.append(f"📅 Next Follow-up: {note_followup}")

            note_text = "\n".join(line for line in note_lines if line is not None)

            db.execute(text("""
                INSERT INTO crm_lead_notes
                    (company_id, lead_id, note, is_private, created_by_type, created_by_id, created_at, updated_at)
                VALUES
                    (4, :lid, :note, FALSE, 'ai_agent', :agent, NOW(), NOW())
            """), {"lid": target_lead_id, "note": note_text, "agent": agent})
        except Exception as _ne:
            logger.warning(f"[STATUS] CRM note insert failed lead={target_lead_id}: {_ne}")

    a_name     = analysis.get("customer_name")  or None
    a_phone    = analysis.get("customer_phone") or None
    a_email    = analysis.get("customer_email") or None
    a_city     = analysis.get("city")           or None
    a_loc      = analysis.get("location_preference") or None
    a_prop     = analysis.get("property_type")  or None
    a_bmin     = _to_float(analysis.get("budget_min"))
    a_bmax     = _to_float(analysis.get("budget_max"))
    a_req      = analysis.get("requirements")   or None
    a_timeline = analysis.get("timeline")       or None
    a_notes    = analysis.get("notes")          or None
    a_followup = analysis.get("next_follow_up_date") or None
    a_interest = analysis.get("interest_level") or None
    # Build a rich comment string for recent_comments
    comment_parts = []
    if summary:   comment_parts.append(f"[AI Summary] {summary}")
    if a_notes:   comment_parts.append(f"[Notes] {a_notes}")
    if a_timeline:comment_parts.append(f"[Timeline] {a_timeline}")
    if a_interest:comment_parts.append(f"[Interest] {a_interest}")
    rich_comment = " | ".join(comment_parts) or None

    # Map AI call outcome to CRM pipeline status progression
    _OUTCOME_TO_CRM_STATUS = {
        "interested":     "interested",
        "qualified":      "qualified",
        "callback":       "contacted",
        "connected":      "contacted",
        "in_progress":    "contacted",
        "not_interested": "lost",
    }
    new_crm_status = _OUTCOME_TO_CRM_STATUS.get(outcome or "", None)

    # ── If lead_id exists → update it with all extracted info ─────────────────
    if lead_id:
        status_update_clause = (
            "status = CASE WHEN status NOT IN ('won','qualified','proposal','loan_process') THEN :new_crm_status ELSE status END,"
            if new_crm_status else ""
        )
        db.execute(text(f"""
            UPDATE crm_leads
            SET ai_status          = :outcome,
                ai_summary         = :summary,
                ai_language        = :lang,
                ai_last_called_at  = NOW(),
                ai_call_count      = COALESCE(ai_call_count, 0) + 1,
                last_contact_date  = NOW(),
                updated_at         = NOW(),
                {status_update_clause}
                name               = COALESCE(NULLIF(:aname,''),  name),
                email              = COALESCE(NULLIF(:aemail,''), email),
                city               = COALESCE(NULLIF(:acity,''),  city),
                looking_for        = COALESCE(NULLIF(:aloc,''),   looking_for),
                requirements       = COALESCE(NULLIF(:areq,''),   requirements),
                budget_min         = COALESCE(:abmin, budget_min),
                budget_max         = COALESCE(:abmax, budget_max),
                next_followup_date = CASE WHEN :afollowup::date IS NOT NULL
                                         THEN :afollowup::date ELSE next_followup_date END,
                recent_comments    = CASE WHEN :rcomment IS NOT NULL
                                         THEN :rcomment ELSE recent_comments END
            WHERE id = :lid
        """), {
            "outcome": outcome or "no_answer", "summary": summary,
            "lang": detected_lang, "lid": lead_id,
            "aname": a_name, "aemail": a_email, "acity": a_city,
            "aloc": (f"{a_loc} | {a_prop}" if a_loc and a_prop else a_loc or a_prop),
            "areq": a_req, "abmin": a_bmin, "abmax": a_bmax,
            "afollowup": a_followup,
            "rcomment": rich_comment,
            **({"new_crm_status": new_crm_status} if new_crm_status else {}),
        })
        # Snapshot crm_status_after for history tracking
        updated_status = db.execute(text(
            "SELECT status FROM crm_leads WHERE id = :lid"
        ), {"lid": lead_id}).scalar()
        db.execute(text(
            "UPDATE ai_call_logs SET crm_status_after = :csa WHERE id = :lid"
        ), {"csa": updated_status, "lid": log_id})
        # Write CRM note visible in lead timeline
        _agent = _get_agent_name_for_log(log_id)
        _status_before_snap = db.execute(text(
            "SELECT crm_status_before FROM ai_call_logs WHERE id=:lid"
        ), {"lid": log_id}).scalar()
        _write_ai_call_note(lead_id, _agent, outcome or "no_answer", summary,
                            _status_before_snap, updated_status,
                            detected_lang, duration, a_followup, rich_comment)

    else:
        # ── No lead_id — try to find by phone, or create a new lead ──────────
        # (This happens for manual test calls that weren't tied to a CRM lead)
        phone_from_log = db.execute(text(
            "SELECT l.phone_dialed FROM ai_call_logs l WHERE l.id = :lid"
        ), {"lid": log_id}).scalar()
        phone_to_use = a_phone or phone_from_log

        if phone_to_use:
            existing = db.execute(text(
                "SELECT id FROM crm_leads WHERE phone = :ph AND company_id = :cid LIMIT 1"
            ), {"ph": phone_to_use, "cid": 4}).fetchone()

            if existing:
                lead_id = existing[0]
                phone_status_clause = (
                    "status = CASE WHEN status NOT IN ('won','qualified','proposal','loan_process') THEN :new_crm_status ELSE status END,"
                    if new_crm_status else ""
                )
                db.execute(text(f"""
                    UPDATE crm_leads
                    SET ai_status=:outcome, ai_summary=:summary, ai_language=:lang,
                        ai_last_called_at=NOW(), ai_call_count=COALESCE(ai_call_count,0)+1,
                        last_contact_date=NOW(), updated_at=NOW(),
                        {phone_status_clause}
                        city               = COALESCE(NULLIF(:acity,''),  city),
                        looking_for        = COALESCE(NULLIF(:aloc,''),   looking_for),
                        requirements       = COALESCE(NULLIF(:areq,''),   requirements),
                        budget_min         = COALESCE(:abmin, budget_min),
                        budget_max         = COALESCE(:abmax, budget_max),
                        next_followup_date = CASE WHEN :afollowup::date IS NOT NULL
                                                 THEN :afollowup::date ELSE next_followup_date END,
                        recent_comments    = CASE WHEN :rcomment IS NOT NULL
                                                 THEN :rcomment ELSE recent_comments END
                    WHERE id = :lid
                """), {
                    "outcome": outcome or "no_answer", "summary": summary,
                    "lang": detected_lang, "lid": lead_id,
                    "acity": a_city, "aloc": (f"{a_loc} | {a_prop}" if a_loc and a_prop else a_loc or a_prop),
                    "areq": a_req, "abmin": a_bmin, "abmax": a_bmax,
                    "afollowup": a_followup, "rcomment": rich_comment,
                    **({"new_crm_status": new_crm_status} if new_crm_status else {}),
                })
                # Link the log to this lead + snapshot crm_status_after
                updated_status_p = db.execute(text(
                    "SELECT status FROM crm_leads WHERE id = :lid"
                ), {"lid": lead_id}).scalar()
                db.execute(text(
                    "UPDATE ai_call_logs SET lead_id=:lid, crm_status_after=:csa WHERE id=:log"
                ), {"lid": lead_id, "csa": updated_status_p, "log": log_id})
                # Write CRM note
                _agent_p = _get_agent_name_for_log(log_id)
                _status_before_p = db.execute(text(
                    "SELECT crm_status_before FROM ai_call_logs WHERE id=:lid"
                ), {"lid": log_id}).scalar()
                _write_ai_call_note(lead_id, _agent_p, outcome or "no_answer", summary,
                                    _status_before_p, updated_status_p,
                                    detected_lang, duration, a_followup, rich_comment)

            elif outcome in QUALIFIED_OUTCOMES or (a_interest and a_interest in ("high", "medium")):
                # Only auto-create a new lead if there's genuine interest
                new_lead = db.execute(text("""
                    INSERT INTO crm_leads
                        (company_id, name, phone, email, city, looking_for, requirements,
                         budget_min, budget_max, source, status, priority, description,
                         ai_status, ai_summary, ai_language, ai_last_called_at, ai_call_count,
                         next_followup_date, last_contact_date, recent_comments,
                         created_at, updated_at)
                    VALUES
                        (4, :aname, :phone, :aemail, :acity, :aloc, :areq,
                         :abmin, :abmax, 'AI Call', 'New', 'medium',
                         :desc, :outcome, :summary, :lang, NOW(), 1,
                         :afollowup, NOW(), :rcomment, NOW(), NOW())
                    RETURNING id
                """), {
                    "aname": a_name or "Unknown", "phone": phone_to_use,
                    "aemail": a_email, "acity": a_city,
                    "aloc": (f"{a_loc} | {a_prop}" if a_loc and a_prop else a_loc or a_prop),
                    "areq": a_req, "abmin": a_bmin, "abmax": a_bmax,
                    "desc": f"Auto-created from AI call. Timeline: {a_timeline or 'Not mentioned'}",
                    "outcome": outcome or "no_answer", "summary": summary, "lang": detected_lang,
                    "afollowup": a_followup, "rcomment": rich_comment,
                }).fetchone()
                if new_lead:
                    db.execute(text("UPDATE ai_call_logs SET lead_id=:lid WHERE id=:log"),
                               {"lid": new_lead[0], "log": log_id})
                    logger.info(f"[STATUS] ✅ New CRM lead created id={new_lead[0]} log={log_id}")
                    # Write CRM note for the new lead
                    _agent_n = _get_agent_name_for_log(log_id)
                    _write_ai_call_note(new_lead[0], _agent_n, outcome or "no_answer", summary,
                                        None, "contacted", detected_lang, duration,
                                        a_followup, rich_comment)

    if campaign_id:
        db.execute(text("""
            UPDATE ai_campaigns
            SET calls_made = COALESCE(calls_made,0)+1,
                calls_connected = COALESCE(calls_connected,0) + CASE WHEN :connected THEN 1 ELSE 0 END,
                calls_qualified = COALESCE(calls_qualified,0) + CASE WHEN :qualified THEN 1 ELSE 0 END,
                updated_at = NOW()
            WHERE id=:cid
        """), {
            "connected": final_status == "completed",
            "qualified": outcome in QUALIFIED_OUTCOMES,
            "cid": campaign_id,
        })

    db.commit()
    _clean_old_audio()

    # Auto-advance: dial next lead(s) to keep concurrency filled
    if campaign_id:
        try:
            _try_advance_campaign(db, campaign_id, _webhook_base(request))
        except Exception as adv_err:
            logger.error(f"[AI_CALLING] Auto-advance error: {adv_err}")

    return Response(content="OK", media_type="text/plain")


def _finalize_call(db: Session, log_id: int, outcome: str, transcript: list,
                   lang: str, campaign_id: int):
    """Mark a call as complete mid-conversation when AI decides to end."""
    try:
        analysis = _gpt_summarize(transcript, lang)
        summary  = analysis.get("summary", "")
    except Exception:
        summary = ""
    db.execute(text("""
        UPDATE ai_call_logs SET outcome=:outcome, ai_summary=:summary WHERE id=:id
    """), {"outcome": outcome, "summary": summary, "id": log_id})
    db.commit()


# ─────────────────────────────────────────────────────────
# USAGE & COST ANALYTICS  (VGK Mentor / Accounts only)
# ─────────────────────────────────────────────────────────

def _is_usage_authorized(user: StaffEmployee) -> bool:
    """Allow VGK Mentor (vgk_role == VGK_MENTOR) or Accounts/Finance dept staff."""
    vgk_role = (getattr(user, 'vgk_role', '') or '').upper().strip()
    if vgk_role == 'VGK_MENTOR':
        return True
    role = getattr(user, 'role', None)
    if role:
        rc = (getattr(role, 'role_code', '') or '').lower().strip()
        if rc in {'accounts', 'finance', 'vgk4u', 'vgk4u_supreme', 'key_leadership',
                  'leadership_role', 'accounts_manager', 'hr_manager'}:
            return True
    dept = getattr(user, 'department', None)
    if dept:
        dept_name = (getattr(dept, 'name', '') or '').lower()
        if 'accounts' in dept_name or 'finance' in dept_name:
            return True
    return False


@router.get("/usage-stats")
def get_usage_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Usage & cost analytics for OpenAI (GPT + TTS) and Twilio calls.

    Access: VGK Mentor or Accounts/Finance department only.
    Returns aggregated totals, daily breakdown, and per-call summary.
    """
    if not _is_usage_authorized(current_user):
        raise HTTPException(status_code=403,
                            detail="Access restricted to VGK Mentor and Accounts department staff.")
    cid = current_user.base_company_id

    # ── OpenAI totals ─────────────────────────────────────────────────────────
    openai_rows = db.execute(text("""
        SELECT
            event_type,
            source,
            COUNT(*)                          AS calls,
            COALESCE(SUM(input_tokens),0)     AS input_tokens,
            COALESCE(SUM(output_tokens),0)    AS output_tokens,
            COALESCE(SUM(characters),0)       AS characters,
            COALESCE(SUM(estimated_cost_usd),0) AS cost_usd
        FROM ai_usage_log
        WHERE company_id=:cid
          AND created_at >= NOW() - INTERVAL ':days days'
        GROUP BY event_type, source
        ORDER BY event_type, source
    """.replace(":days", str(days))), {"cid": cid}).fetchall()

    openai_summary = []
    total_openai_cost = 0.0
    kb_hits = 0
    gpt_calls = 0
    for r in openai_rows:
        cost = float(r[6])
        total_openai_cost += cost
        entry = {
            "event_type": r[0], "source": r[1],
            "count": r[2], "input_tokens": r[3],
            "output_tokens": r[4], "characters": r[5],
            "cost_usd": round(cost, 6),
        }
        openai_summary.append(entry)
        if r[0] == "kb_hit":
            kb_hits = r[2]
        if r[0] == "gpt4o_call":
            gpt_calls = r[2]

    # ── Daily breakdown ───────────────────────────────────────────────────────
    daily_rows = db.execute(text("""
        SELECT
            DATE(created_at AT TIME ZONE 'Asia/Kolkata') AS day,
            event_type,
            COUNT(*)                              AS calls,
            COALESCE(SUM(estimated_cost_usd),0)  AS cost_usd
        FROM ai_usage_log
        WHERE company_id=:cid
          AND created_at >= NOW() - INTERVAL ':days days'
        GROUP BY day, event_type
        ORDER BY day DESC, event_type
    """.replace(":days", str(days))), {"cid": cid}).fetchall()

    daily = {}
    for r in daily_rows:
        day = str(r[0])
        daily.setdefault(day, {"date": day, "gpt4o_call": 0, "tts_generation": 0,
                                "kb_hit": 0, "cost_usd": 0.0})
        daily[day][r[1]] = r[2]
        daily[day]["cost_usd"] += float(r[3])
    daily_list = sorted(daily.values(), key=lambda x: x["date"], reverse=True)

    # ── Twilio call costs from ai_call_logs ──────────────────────────────────
    twilio_rows = db.execute(text("""
        SELECT
            COUNT(*)                              AS total_calls,
            COUNT(*) FILTER (WHERE status='completed') AS completed_calls,
            COALESCE(SUM(duration_seconds),0)     AS total_seconds,
            COALESCE(AVG(duration_seconds) FILTER (WHERE duration_seconds>0), 0) AS avg_seconds
        FROM ai_call_logs
        WHERE company_id=:cid
          AND created_at >= NOW() - INTERVAL ':days days'
    """.replace(":days", str(days))), {"cid": cid}).fetchone()

    total_min   = float(twilio_rows[2] or 0) / 60.0
    twilio_cost = round(total_min * _TWILIO_PER_MIN_USD, 4)

    # ── KB savings calculation ────────────────────────────────────────────────
    # Each KB hit saved one GPT call; estimate avg cost of a GPT call
    avg_gpt_cost = (total_openai_cost / gpt_calls) if gpt_calls > 0 else 0.003
    kb_saved_usd = round(kb_hits * avg_gpt_cost, 4)

    return {
        "success": True,
        "period_days": days,
        "pricing_note": "OpenAI: GPT-4o $2.50/1M in + $10/1M out; TTS-1-HD $30/1M chars. "
                        "Twilio: ~$0.0085/min blended (outbound India, carrier fees included).",
        "openai": {
            "total_cost_usd": round(total_openai_cost, 4),
            "breakdown": openai_summary,
            "gpt_calls": gpt_calls,
            "kb_hits": kb_hits,
            "kb_saved_usd": kb_saved_usd,
        },
        "twilio": {
            "total_calls": twilio_rows[0] or 0,
            "completed_calls": twilio_rows[1] or 0,
            "total_minutes": round(total_min, 2),
            "avg_duration_seconds": round(float(twilio_rows[3] or 0), 1),
            "estimated_cost_usd": twilio_cost,
        },
        "daily": daily_list[:60],
        "grand_total_usd": round(total_openai_cost + twilio_cost, 4),
    }


# ─────────────────────────────────────────────────────────
# AUDIO FILE SERVING
# ─────────────────────────────────────────────────────────

@router.get("/audio/{filename}")
def serve_audio(filename: str):
    """Serve TTS audio files to Twilio. Supports both G.711 µ-law WAV and legacy MP3."""
    import time as _time
    safe_name = os.path.basename(filename)
    if "/" in safe_name or ".." in safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not (safe_name.endswith(".wav") or safe_name.endswith(".mp3")):
        raise HTTPException(status_code=400, detail="Invalid filename")
    filepath = os.path.join(AI_AUDIO_DIR, safe_name)
    # Brief retry loop — background TTS may still be writing the file
    for _attempt in range(6):
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            break
        _time.sleep(0.8)
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        # File missing (e.g. server restarted, tmp cleared) — return silent TwiML
        # so Twilio never says "Application Error" to the customer
        logger.warning(f"[AI-AUDIO] File not found after retries: {safe_name} — returning silent fallback")
        twiml_fallback = """<?xml version="1.0" encoding="UTF-8"?><Response><Pause length="1"/></Response>"""
        return Response(content=twiml_fallback, media_type="application/xml", status_code=200)
    media_type = "audio/wav" if safe_name.endswith(".wav") else "audio/mpeg"
    return FileResponse(filepath, media_type=media_type)


# ─────────────────────────────────────────────────────────
# CALL LOGS
# ─────────────────────────────────────────────────────────

@router.get("/campaigns/{campaign_id}/logs")
def get_campaign_logs(
    campaign_id: int,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    campaign = db.execute(text(
        "SELECT id FROM ai_campaigns WHERE id=:id AND company_id=:cid AND status != 'deleted'"
    ), {"id": campaign_id, "cid": current_user.base_company_id}).fetchone()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    total = db.execute(text(
        "SELECT COUNT(*) FROM ai_call_logs WHERE campaign_id=:cid"
    ), {"cid": campaign_id}).fetchone()[0]

    rows = db.execute(text("""
        SELECT l.id, l.lead_id, c.name, c.phone, l.phone_dialed, l.language_used,
               l.attempt_number, l.status, l.outcome, l.duration_seconds,
               l.ai_summary, l.started_at, l.ended_at, l.transcript,
               (SELECT MIN(l2.started_at) FROM ai_call_logs l2
                WHERE l2.phone_dialed = l.phone_dialed AND l2.campaign_id = l.campaign_id) AS first_called_at
        FROM ai_call_logs l
        LEFT JOIN crm_leads c ON c.id = l.lead_id
        WHERE l.campaign_id = :cid
        ORDER BY l.started_at DESC
        LIMIT :lim OFFSET :off
    """), {"cid": campaign_id, "lim": limit, "off": offset}).fetchall()

    return {
        "success": True, "total": total,
        "logs": [
            {
                "id": r[0], "lead_id": r[1], "lead_name": r[2], "lead_phone": r[3],
                "phone_dialed": r[4], "language": r[5], "attempt": r[6],
                "status": r[7], "outcome": r[8], "duration_seconds": r[9],
                "ai_summary": r[10],
                "started_at": r[11].isoformat() if r[11] else None,
                "ended_at": r[12].isoformat() if r[12] else None,
                "has_transcript": bool(r[13] and r[13] != "[]"),
                "first_called_at": r[14].isoformat() if r[14] else None,
            }
            for r in rows
        ],
    }


@router.get("/logs/{log_id}/transcript")
def get_log_transcript(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    row = db.execute(text("""
        SELECT l.transcript, l.ai_summary, l.outcome, l.language_used,
               l.duration_seconds, l.started_at
        FROM ai_call_logs l
        LEFT JOIN ai_campaigns c ON c.id = l.campaign_id
        WHERE l.id=:id
          AND (l.company_id=:cid OR c.company_id=:cid)
    """), {"id": log_id, "cid": current_user.base_company_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Log not found")
    try:
        transcript = json.loads(row[0] or "[]")
    except Exception:
        transcript = []
    return {
        "success": True,
        "transcript": transcript,
        "ai_summary": row[1],
        "outcome": row[2],
        "language": row[3],
        "duration_seconds": row[4],
        "started_at": row[5].isoformat() if row[5] else None,
    }


@router.get("/logs")
def get_all_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    phone: str = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Recent call logs across all campaigns for this company (includes test calls).
    Optional ?phone= filter returns all logs for a specific number."""
    phone_clause = "AND (l.phone_dialed = :phone OR cl.phone = :phone)" if phone else ""
    params: dict = {"cid": current_user.base_company_id}
    if phone:
        params["phone"] = phone

    total = db.execute(text(
        f"SELECT COUNT(*) FROM ai_call_logs l LEFT JOIN crm_leads cl ON cl.id = l.lead_id "
        f"WHERE l.company_id=:cid {phone_clause}"
    ), params).fetchone()[0]

    rows = db.execute(text(f"""
        SELECT l.id, l.lead_id, cl.name, cl.phone, l.phone_dialed, l.language_used,
               l.attempt_number, l.status, l.outcome, l.duration_seconds,
               l.ai_summary, l.started_at, l.ended_at, l.transcript,
               c.name as campaign_name, l.campaign_id, l.recording_url,
               l.segment, l.crm_status_before, l.crm_status_after,
               cl.status as current_crm_status
        FROM ai_call_logs l
        LEFT JOIN crm_leads cl ON cl.id = l.lead_id
        LEFT JOIN ai_campaigns c ON c.id = l.campaign_id
        WHERE l.company_id = :cid {phone_clause}
        ORDER BY l.started_at DESC
        LIMIT :lim OFFSET :off
    """), {**params, "lim": limit, "off": offset}).fetchall()

    return {
        "success": True, "total": total,
        "logs": [
            {
                "id": r[0], "lead_id": r[1], "lead_name": r[2], "lead_phone": r[3],
                "phone_dialed": r[4], "language": r[5], "attempt": r[6],
                "status": r[7], "outcome": r[8], "duration_seconds": r[9],
                "ai_summary": r[10],
                "started_at": r[11].isoformat() if r[11] else None,
                "ended_at": r[12].isoformat() if r[12] else None,
                "has_transcript": bool(r[13] and r[13] != "[]"),
                "campaign_name": r[14],
                "campaign_id": r[15],
                "recording_url": r[16],
                "segment": r[17] or "",
                "crm_status_before": r[18] or "",
                "crm_status_after": r[19] or "",
                "current_crm_status": r[20] or "",
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────
# LEAD RECORDINGS — fetch AI call recordings for a CRM lead
# ─────────────────────────────────────────────────────────

@router.get("/lead-recordings/{lead_id}")
def get_lead_recordings(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Return all AI call logs (with recordings) for a given CRM lead_id."""
    rows = db.execute(text("""
        SELECT l.id, l.started_at, l.duration_seconds, l.outcome,
               l.recording_url, l.language_used, l.ai_summary,
               s.agent_name, l.crm_status_before, l.crm_status_after
        FROM ai_call_logs l
        LEFT JOIN ai_call_sessions s ON s.call_sid = l.call_sid
        WHERE l.lead_id = :lid
        ORDER BY l.started_at DESC
        LIMIT 50
    """), {"lid": lead_id}).fetchall()

    return {
        "success": True,
        "recordings": [
            {
                "log_id": r[0],
                "started_at": r[1].isoformat() if r[1] else None,
                "duration_seconds": r[2] or 0,
                "outcome": r[3] or "no_answer",
                "recording_url": r[4],
                "language": r[5] or "hi",
                "summary": r[6],
                "agent": r[7] or "Vidya",
                "crm_before": r[8],
                "crm_after": r[9],
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    stats = db.execute(text("""
        SELECT
            COUNT(*)                                             AS total_campaigns,
            COUNT(*) FILTER (WHERE status='active')             AS active_campaigns,
            COALESCE(SUM(calls_made), 0)                        AS total_calls_made,
            COALESCE(SUM(calls_connected), 0)                   AS total_connected,
            COALESCE(SUM(calls_qualified), 0)                   AS total_qualified
        FROM ai_campaigns
        WHERE company_id = :cid AND status != 'deleted'
    """), {"cid": current_user.base_company_id}).fetchone()

    lang_stats = db.execute(text("""
        SELECT language_used, COUNT(*), outcome
        FROM ai_call_logs l
        JOIN ai_campaigns c ON c.id = l.campaign_id
        WHERE c.company_id = :cid
        GROUP BY language_used, outcome
    """), {"cid": current_user.base_company_id}).fetchall()

    cat_entries = db.execute(text("""
        SELECT COUNT(*) FROM ai_product_catalogue WHERE company_id=:cid AND is_active=TRUE
    """), {"cid": current_user.base_company_id}).fetchone()

    return {
        "success": True,
        "campaigns": {
            "total": stats[0], "active": stats[1],
            "calls_made": stats[2], "calls_connected": stats[3],
            "calls_qualified": stats[4],
        },
        "language_breakdown": [
            {"language": r[0], "count": r[1], "outcome": r[2]} for r in lang_stats
        ],
        "catalogue_entries": cat_entries[0] if cat_entries else 0,
    }


# ─────────────────────────────────────────────────────────
# EXECUTIVE DASHBOARD STATS
# ─────────────────────────────────────────────────────────

@router.get("/stats/executive")
def get_executive_stats(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    campaign_id: Optional[int] = Query(None),
    segment: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Executive dashboard — aggregated campaign, agent, language, outcome and CRM conversion stats."""
    cid = current_user.base_company_id
    params: dict = {"cid": cid}
    time_clause = ""
    if date_from:
        time_clause += " AND l.started_at >= :date_from"
        params["date_from"] = date_from
    if date_to:
        time_clause += " AND l.started_at < :date_to"
        params["date_to"] = date_to
    camp_clause = ""
    if campaign_id:
        camp_clause = " AND l.campaign_id = :camp_id"
        params["camp_id"] = campaign_id
    seg_clause = ""
    if segment:
        seg_clause = " AND c.campaign_segment = :seg"
        params["seg"] = segment

    base_join = """
        FROM ai_call_logs l
        LEFT JOIN ai_campaigns c ON c.id = l.campaign_id
        WHERE l.company_id = :cid
    """ + time_clause + camp_clause + seg_clause

    # ── Overall summary ──────────────────────────────────
    summary = db.execute(text(f"""
        SELECT
            COUNT(*)                                                 AS total_calls,
            COUNT(*) FILTER (WHERE l.status = 'completed')          AS completed,
            COUNT(*) FILTER (WHERE l.outcome IS NOT NULL
                               AND l.outcome NOT IN ('no_answer','busy','failed','canceled'))
                                                                     AS connected,
            COUNT(*) FILTER (WHERE l.outcome IN ('interested','qualified','callback'))
                                                                     AS qualified,
            COUNT(*) FILTER (WHERE l.outcome = 'not_interested')    AS not_interested,
            COUNT(*) FILTER (WHERE l.outcome IN ('no_answer','busy','failed'))
                                                                     AS no_contact,
            ROUND(AVG(l.duration_seconds) FILTER (WHERE l.duration_seconds > 0)) AS avg_duration,
            COUNT(DISTINCT l.lead_id) FILTER (WHERE l.lead_id IS NOT NULL)
                                                                     AS unique_leads,
            COUNT(DISTINCT l.lead_id) FILTER (
                WHERE l.outcome IN ('interested','qualified','callback')
                  AND l.lead_id IS NOT NULL)                         AS unique_qualified
        {base_join}
    """), params).fetchone()

    # ── Campaign performance ─────────────────────────────
    camp_rows = db.execute(text(f"""
        SELECT c.id, c.name, c.campaign_segment,
               COUNT(l.id)                                           AS calls,
               COUNT(l.id) FILTER (WHERE l.outcome IN ('interested','qualified','callback'))
                                                                     AS qualified,
               COUNT(l.id) FILTER (WHERE l.outcome NOT IN ('no_answer','busy','failed','canceled')
                                     AND l.outcome IS NOT NULL)      AS connected,
               ROUND(AVG(l.duration_seconds) FILTER (WHERE l.duration_seconds > 0)) AS avg_dur,
               COUNT(DISTINCT l.lead_id) FILTER (
                   WHERE l.outcome IN ('interested','qualified','callback')
                     AND l.lead_id IS NOT NULL)                      AS unique_qualified
        FROM ai_call_logs l
        LEFT JOIN ai_campaigns c ON c.id = l.campaign_id
        WHERE l.company_id = :cid {time_clause} {camp_clause} {seg_clause}
        GROUP BY c.id, c.name, c.campaign_segment
        ORDER BY calls DESC LIMIT 20
    """), params).fetchall()

    # ── Agent breakdown (Vidya vs Karthik) ──────────────
    agent_rows = db.execute(text(f"""
        SELECT s.agent_name,
               COUNT(DISTINCT l.id)                                  AS calls,
               COUNT(DISTINCT l.id) FILTER (WHERE l.outcome IN ('interested','qualified','callback'))
                                                                     AS qualified,
               ROUND(AVG(l.duration_seconds) FILTER (WHERE l.duration_seconds > 0)) AS avg_dur
        FROM ai_call_logs l
        LEFT JOIN ai_call_sessions s ON s.call_sid = l.call_sid
        WHERE l.company_id = :cid {time_clause} {camp_clause} {seg_clause}
        GROUP BY s.agent_name
    """), params).fetchall()

    # ── Language breakdown ───────────────────────────────
    lang_rows = db.execute(text(f"""
        SELECT l.language_used, COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE l.outcome IN ('interested','qualified','callback')) AS qualified
        {base_join}
        GROUP BY l.language_used
    """), params).fetchall()

    # ── Outcome funnel ───────────────────────────────────
    outcome_rows = db.execute(text(f"""
        SELECT COALESCE(l.outcome, 'no_answer') AS outcome, COUNT(*) AS cnt
        {base_join}
        GROUP BY outcome ORDER BY cnt DESC
    """), params).fetchall()

    # ── CRM status conversion (leads where status changed) ──
    conv_rows = db.execute(text(f"""
        SELECT l.crm_status_before, l.crm_status_after, COUNT(*) AS cnt
        {base_join}
        AND l.crm_status_before IS NOT NULL AND l.crm_status_after IS NOT NULL
          AND l.crm_status_before != l.crm_status_after
        GROUP BY l.crm_status_before, l.crm_status_after
        ORDER BY cnt DESC LIMIT 15
    """), params).fetchall()

    # ── Daily call volume (last 30 days or date range) ──
    daily_rows = db.execute(text(f"""
        SELECT DATE(l.started_at) AS day, COUNT(*) AS calls,
               COUNT(*) FILTER (WHERE l.outcome IN ('interested','qualified','callback')) AS qualified
        {base_join}
        GROUP BY day ORDER BY day DESC LIMIT 30
    """), params).fetchall()

    return {
        "success": True,
        "summary": {
            "total_calls": summary[0] or 0,
            "completed": summary[1] or 0,
            "connected": summary[2] or 0,
            "qualified": summary[3] or 0,
            "not_interested": summary[4] or 0,
            "no_contact": summary[5] or 0,
            "avg_duration_seconds": int(summary[6] or 0),
            "unique_leads": summary[7] or 0,
            "unique_qualified": summary[8] or 0,
            "connect_rate": round((summary[2] or 0) / max(summary[0] or 1, 1) * 100, 1),
            "qualify_rate": round((summary[3] or 0) / max(summary[2] or 1, 1) * 100, 1),
        },
        "campaigns": [
            {
                "id": r[0], "name": r[1] or "Test/Direct", "segment": r[2] or "",
                "calls": r[3], "qualified": r[4], "connected": r[5], "avg_duration": int(r[6] or 0),
                "unique_qualified": r[7] or 0,
                "connect_rate": round((r[5] or 0) / max(r[3] or 1, 1) * 100, 1),
                "qualify_rate": round((r[4] or 0) / max(r[5] or 1, 1) * 100, 1),
            }
            for r in camp_rows
        ],
        "agents": [
            {
                "name": r[0] or "Unknown", "calls": r[1], "qualified": r[2],
                "avg_duration": int(r[3] or 0),
            }
            for r in agent_rows
        ],
        "languages": [
            {"language": r[0] or "unknown", "calls": r[1], "qualified": r[2]}
            for r in lang_rows
        ],
        "outcomes": [
            {"outcome": r[0], "count": r[1]} for r in outcome_rows
        ],
        "status_conversions": [
            {"from": r[0], "to": r[1], "count": r[2]} for r in conv_rows
        ],
        "daily_volume": [
            {"date": str(r[0]), "calls": r[1], "qualified": r[2]}
            for r in daily_rows
        ],
    }


# ─────────────────────────────────────────────────────────
# STAFF SEARCH (for assignment)
# ─────────────────────────────────────────────────────────

@router.get("/staff-search")
def search_staff(
    q: str = Query(""),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    rows = db.execute(text("""
        SELECT e.emp_code, e.full_name, d.name as department
        FROM staff_employees e
        LEFT JOIN staff_departments d ON d.id = e.department_id
        WHERE e.base_company_id = :cid AND e.status = 'active'
          AND (e.emp_code ILIKE :q OR e.full_name ILIKE :q OR d.name ILIKE :q)
        ORDER BY e.full_name LIMIT 30
    """), {"cid": current_user.base_company_id, "q": f"%{q}%"}).fetchall()
    return {"success": True, "staff": [
        {"emp_code": r[0], "name": r[1], "department": r[2]} for r in rows
    ]}


# ─────────────────────────────────────────────────────────
# VOICE SETTINGS
# ─────────────────────────────────────────────────────────

@router.get("/voice-settings")
def get_voice_settings(
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    cid = current_user.base_company_id
    row = db.execute(
        text("SELECT value FROM ai_settings WHERE company_id=:cid AND key='voice'"),
        {"cid": cid},
    ).fetchone()
    voice = row[0] if row and row[0] in VALID_VOICES else "nova"
    return {"success": True, "voice": voice}


@router.post("/voice-settings")
def save_voice_settings(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    voice = payload.get("voice", "nova")
    if voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail=f"Invalid voice. Must be one of: {VALID_VOICES}")
    cid = current_user.base_company_id
    db.execute(text("""
        INSERT INTO ai_settings (company_id, key, value, updated_at)
        VALUES (:cid, 'voice', :val, NOW())
        ON CONFLICT (company_id, key) DO UPDATE SET value=:val, updated_at=NOW()
    """), {"cid": cid, "val": voice})
    db.commit()
    # Bust the in-memory cache so the next call uses the new voice
    _VOICE_CACHE.pop(cid, None)
    return {"success": True, "voice": voice}


@router.get("/voice-preview")
async def voice_preview(
    voice: str = Query("nova"),
    lang: str  = Query("hi"),
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user),
):
    """Generate a short TTS sample for the given voice + language and return its URL."""
    if voice not in VALID_VOICES:
        raise HTTPException(status_code=400, detail="Invalid voice")
    samples = {
        "hi": "Namaste! Main Vidya bol rahi hoon Mynt Real LLP se. Aapke sawal ka jawab dene mein khushi hogi.",
        "te": "Namaskaram! Nenu Vidya ni, Mynt Real LLP nundi. Mee savalaki samadhaanam ivvaniki chaala santhosham.",
        "en": "Hello! This is Vidya from Mynt Real LLP. I'm here to help you with all your property queries.",
    }
    sample_text = samples.get(lang, samples["hi"])
    try:
        fname = await asyncio.to_thread(_generate_tts, sample_text, lang, voice)
        # Return relative URL — the frontend constructs the full URL with its base
        return {"success": True, "url": f"/api/v1/staff/ai-calling/audio/{fname}", "voice": voice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
