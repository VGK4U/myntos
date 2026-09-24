"""
Sarvam AI Telephony Adapter for MyntOS Real-Time AI Calling.

Provides low-latency, real-time bidirectional audio integration:
1. Sarvam Realtime STT (WebSocket: wss://api.sarvam.ai/speech-to-text-realtime/ws)
   - Model: saaras:v3-realtime
   - Audio: Native 8kHz G.711 μ-law (direct pass-through from Plivo without decoding)
   - Languages: auto, te-IN, hi-IN, en-IN
   - Turn & VAD detection for real-time speech detection and instant barge-in.
2. Sarvam Streaming TTS (WebSocket: wss://api.sarvam.ai/text-to-speech/ws)
   - Model: bulbul:v3
   - Audio: 8kHz output matching Plivo telecom standards.
   - Speakers: Vidya / Shubh / Priya / Aditya.
3. Plivo Real-Time Bridge & Interruption (Barge-In) Manager.
4. Tenant-Scoped Dynamic Knowledge Grounding Bridge (No static segment lock).
"""

import os
import json
import base64
import asyncio
import time
import logging
import re
import ssl
import inspect
from typing import Optional, Callable, Dict, Any, List, Tuple
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# Constants
SARVAM_STT_WS_URL = "wss://api.sarvam.ai/speech-to-text-realtime/ws"
SARVAM_TTS_WS_URL = "wss://api.sarvam.ai/text-to-speech/ws"

SUPPORTED_LANGUAGES = {
    "auto": "auto",
    "te": "te-IN",
    "te-IN": "te-IN",
    "hi": "hi-IN",
    "hi-IN": "hi-IN",
    "en": "en-IN",
    "en-IN": "en-IN",
}


def get_sarvam_api_key() -> Optional[str]:
    """Retrieve Sarvam API key from environment, settings, or .env files."""
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        try:
            from app.core.config import settings
            key = (getattr(settings, "SARVAM_API_KEY", "") or "").strip()
        except Exception:
            pass
    if not key:
        try:
            from dotenv import dotenv_values
            backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            if os.path.exists(backend_env):
                vals = dotenv_values(backend_env)
                key = (vals.get("SARVAM_API_KEY") or "").strip()
            if not key:
                root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
                if os.path.exists(root_env):
                    vals = dotenv_values(root_env)
                    key = (vals.get("SARVAM_API_KEY") or "").strip()
        except Exception:
            pass
    return key if key else None


def get_sarvam_ssl_context() -> ssl.SSLContext:
    """Return an SSL context with certifi CA bundle if available."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def get_ws_connect_kwargs(headers: Dict[str, str], ssl_ctx: Optional[ssl.SSLContext] = None) -> Dict[str, Any]:
    """Return kwargs for websockets.connect compatible with both websockets 14+ and older versions."""
    import websockets
    kwargs: Dict[str, Any] = {}
    if ssl_ctx is not None:
        kwargs["ssl"] = ssl_ctx
    if "additional_headers" in inspect.signature(websockets.connect).parameters:
        kwargs["additional_headers"] = headers
    else:
        kwargs["extra_headers"] = headers
    return kwargs


class SarvamRealtimeSTTClient:
    """
    Manages connection to Sarvam Realtime STT WebSocket using saaras:v3-realtime.
    Accepts raw base64 8kHz mu-law audio chunks directly from Plivo stream.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        language_code: str = "auto",
        model: str = "saaras:v3-realtime",
        encoding: str = "mulaw",
        sample_rate: int = 8000,
        stream_type: str = "balanced",
        endpointing: str = "vad",
        mode: str = "transcribe",
        on_speech_start: Optional[Callable[[], Any]] = None,
        on_partial_transcript: Optional[Callable[[str, str], Any]] = None,
        on_final_transcript: Optional[Callable[[str, str], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
    ):
        self.api_key = api_key or get_sarvam_api_key()
        self.language_code = SUPPORTED_LANGUAGES.get(language_code, "auto")
        self.model = model
        self.encoding = encoding
        self.sample_rate = sample_rate
        self.stream_type = stream_type
        self.endpointing = endpointing
        self.mode = mode

        # Event Callbacks
        self.on_speech_start = on_speech_start
        self.on_partial_transcript = on_partial_transcript
        self.on_final_transcript = on_final_transcript
        self.on_error = on_error

        self.ws = None
        self._running = False
        self._receive_task = None
        self.is_connected = False
        self.last_detected_language = self.language_code

    def build_ws_url(self) -> str:
        """Construct WebSocket URL with query parameters per Sarvam API spec."""
        params = {
            "model": self.model,
            "language_code": self.language_code,
            "encoding": self.encoding,
            "sample_rate": str(self.sample_rate),
            "stream_type": self.stream_type,
            "endpointing": self.endpointing,
            "mode": self.mode,
        }
        return f"{SARVAM_STT_WS_URL}?{urlencode(params)}"

    async def connect(self):
        """Establish WebSocket connection to Sarvam Realtime STT."""
        if not self.api_key:
            logger.warning("[SARVAM-STT] No SARVAM_API_KEY configured — operating in offline mock mode")
            self.is_connected = True
            self._running = True
            return

        import websockets
        url = self.build_ws_url()
        headers = {
            "Api-Subscription-Key": self.api_key
        }

        try:
            ssl_ctx = get_sarvam_ssl_context()
            connect_kwargs = get_ws_connect_kwargs(headers, ssl_ctx=ssl_ctx)
            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10,
                max_size=10 * 1024 * 1024,
                **connect_kwargs,
            )
            self.is_connected = True
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"[SARVAM-STT] Connected to {self.model} ({self.language_code}, {self.encoding}@{self.sample_rate}Hz)")
        except Exception as e:
            logger.error(f"[SARVAM-STT] Connection failed: {e}")
            self.is_connected = False
            self._running = False
            if self.on_error:
                self.on_error(str(e))
            raise

    async def send_audio_chunk(self, base64_audio: str):
        """
        Send base64-encoded audio chunk to Sarvam.
        Plivo passes 8kHz mu-law base64 directly, requiring zero decoding.
        """
        if not self._running:
            return

        if not self.ws:
            # Offline mock handler
            return

        msg = {
            "event": "audio_input",
            "audio": base64_audio
        }
        try:
            await self.ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"[SARVAM-STT] Error sending audio chunk: {e}")
            if self.on_error:
                self.on_error(f"Send audio error: {e}")

    async def _receive_loop(self):
        """Listen for Sarvam STT WebSocket messages."""
        try:
            async for raw_msg in self.ws:
                if not self._running:
                    break
                try:
                    data = json.loads(raw_msg)
                except Exception:
                    continue

                event = data.get("event")
                if event == "session.begin":
                    req_id = data.get("request_id")
                    logger.info(f"[SARVAM-STT] Session began: req_id={req_id}")

                elif event == "vad.speech_start":
                    # Caller started speaking -> Immediate trigger for Barge-In
                    logger.info("[SARVAM-STT] 🎙️ Speech start detected (VAD)")
                    if self.on_speech_start:
                        if asyncio.iscoroutinefunction(self.on_speech_start):
                            await self.on_speech_start()
                        else:
                            self.on_speech_start()

                elif event == "transcript.partial":
                    text = data.get("text", "")
                    lang = data.get("language") or self.last_detected_language
                    if lang:
                        self.last_detected_language = lang
                    if self.on_partial_transcript:
                        if asyncio.iscoroutinefunction(self.on_partial_transcript):
                            await self.on_partial_transcript(text, lang)
                        else:
                            self.on_partial_transcript(text, lang)

                elif event == "transcript.final":
                    text = data.get("text", "")
                    lang = data.get("language") or self.last_detected_language
                    if lang:
                        self.last_detected_language = lang
                    logger.info(f"[SARVAM-STT] 📝 Final Transcript ({lang}): '{text}'")
                    if self.on_final_transcript:
                        if asyncio.iscoroutinefunction(self.on_final_transcript):
                            await self.on_final_transcript(text, lang)
                        else:
                            self.on_final_transcript(text, lang)

                elif event == "error":
                    err_msg = data.get("message", "Unknown Sarvam error")
                    logger.error(f"[SARVAM-STT] Error event: {err_msg}")
                    if self.on_error:
                        self.on_error(err_msg)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[SARVAM-STT] Receive loop error: {e}")
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.is_connected = False

    async def close(self):
        """Gracefully close STT session."""
        self._running = False
        if self.ws:
            try:
                # Send session end signal
                await self.ws.send(json.dumps({"event": "end"}))
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None
        self.is_connected = False

    # Alias for disconnect
    disconnect = close


class SarvamStreamingTTSClient:
    """
    Manages streaming text synthesis with Sarvam bulbul:v3.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "bulbul:v3",
        language_code: str = "te-IN",
        speaker: str = "shubh",
        sample_rate: int = 8000,
        output_codec: str = "mulaw",
    ):
        self.api_key = api_key or get_sarvam_api_key()
        self.model = model
        self.language_code = language_code
        self.speaker = speaker
        self.sample_rate = sample_rate
        self.output_codec = output_codec
        self.ws = None
        self._running = False

    async def synthesize_streaming(
        self,
        text_generator,
        on_audio_chunk: Callable[[str], Any]
    ):
        """
        Stream text chunks into Sarvam TTS and emit base64 audio chunks.
        Falls back to local audio if offline or keys unconfigured.
        """
        if not self.api_key:
            logger.warning("[SARVAM-TTS] No SARVAM_API_KEY — using fallback simulator")
            return

        import websockets
        url = f"{SARVAM_TTS_WS_URL}?model={self.model}&send_completion_event=true"
        headers = {"Api-Subscription-Key": self.api_key}
        ssl_ctx = get_sarvam_ssl_context()
        connect_kwargs = get_ws_connect_kwargs(headers, ssl_ctx=ssl_ctx)

        async with websockets.connect(url, **connect_kwargs) as ws:
            # 1. Send Configure Connection
            config_msg = {
                "type": "config",
                "data": {
                    "model": self.model,
                    "language_code": self.language_code,
                    "speaker": self.speaker.lower(),
                    "speech_sample_rate": str(self.sample_rate),
                    "output_audio_codec": self.output_codec,
                }
            }
            await ws.send(json.dumps(config_msg))

            # 2. Task to read audio chunks from Sarvam
            async def reader():
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        mtype = msg.get("type")
                        if mtype == "audio":
                            audio_b64 = msg.get("data", {}).get("audio", "")
                            if audio_b64 and on_audio_chunk:
                                if asyncio.iscoroutinefunction(on_audio_chunk):
                                    await on_audio_chunk(audio_b64)
                                else:
                                    on_audio_chunk(audio_b64)
                        elif mtype == "event" and msg.get("data", {}).get("event_type") == "final":
                            break
                        elif mtype == "error":
                            logger.error(f"[SARVAM-TTS] Error from server: {msg}")
                            break
                    except Exception as e:
                        logger.warning(f"[SARVAM-TTS] Read error: {e}")
                        break

            reader_task = asyncio.create_task(reader())

            # 3. Stream incoming text chunks
            async for chunk in text_generator:
                clean_chunk = chunk.strip()
                if clean_chunk:
                    await ws.send(json.dumps({
                        "type": "text",
                        "data": {"text": clean_chunk}
                    }))

            # 4. Send flush signal
            await ws.send(json.dumps({"type": "flush"}))
            await reader_task


class DynamicKnowledgeEngine:
    """
    Dynamic Cross-Vertical Knowledge Retrieval Engine.
    Breaks free from static segment='solar' locking.
    Allows customer to naturally transition between Solar, Property, EV, Finance, CIBIL, etc.
    """

    VERTICAL_KEYWORDS = {
        "solar": [
            "solar", "panel", "rooftop", "subsidy", "net metering", "kw", "kilowatt",
            "inverter", "surya", "bijli", "electricity bill", "tata power", "battery",
            "mnre", "3kw", "5kw", "10kw"
        ],
        "property": [
            "property", "plot", "plots", "land", "villa", "apartment", "flat", "sq yard",
            "gaj", "acre", "cent", "rera", "layout", "venture", "bhimili", "vizianagaram",
            "visakhapatnam", "hyderabad", "gated community", "open plot", "construction"
        ],
        "ev": [
            "ev", "electric", "scooter", "bike", "vehicle", "charging", "battery",
            "range", "mileage", "speed", "ather", "ola", "tvs", "two wheeler", "swap"
        ],
        "finance": [
            "finance", "loan", "emi", "bank", "interest", "interest rate", "cibil",
            "score", "down payment", "processing fee", "approval", "hdfc", "sbi", "icici",
            "documents", "eligibility"
        ],
    }

    @classmethod
    def detect_verticals(cls, text: str) -> List[str]:
        """Detect verticals mentioned in customer speech."""
        text_lower = text.lower()
        detected = []
        for vertical, keywords in cls.VERTICAL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected.append(vertical)
        return detected

    @classmethod
    def retrieve_approved_knowledge(
        cls,
        db_session,
        company_id: int,
        question: str,
        active_segment: str = "",
        max_entries: int = 4
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Dynamically query ai_product_catalogue across company's approved records.
        Returns: (matching_records, has_direct_match)
        """
        from sqlalchemy import text
        if not db_session or not question:
            return [], False

        detected_verticals = cls.detect_verticals(question)
        target_vertical = detected_verticals[0] if detected_verticals else (active_segment or "General")

        # Extract search keywords (alphanumeric, length >= 3)
        raw_words = re.findall(r'\b[a-zA-Z0-9]{3,}\b', question.lower())
        stopwords = {"what", "when", "where", "which", "how", "much", "does", "cost", "price",
                     "tell", "about", "your", "have", "with", "from", "also", "want", "need",
                     "naku", "kavali", "undi", "undha", "cheppandi", "entha", "chahiye", "bataiye"}
        keywords = [w for w in raw_words if w not in stopwords]

        # Multi-vertical search query scoped strictly by company_id and is_active=TRUE
        query = """
            SELECT id, segment, category, title, content
            FROM ai_product_catalogue
            WHERE company_id = :cid AND is_active = TRUE
        """
        params: Dict[str, Any] = {"cid": company_id}

        try:
            rows = db_session.execute(text(query), params).fetchall()
        except Exception as e:
            logger.error(f"[DYNAMIC-KB] DB error: {e}")
            return [], False

        scored_records = []
        for row in rows:
            seg = (row[1] or "").lower()
            cat = (row[2] or "").lower()
            title = (row[3] or "").lower()
            content = (row[4] or "").lower()

            score = 0
            # Vertical match boost
            if target_vertical and (target_vertical.lower() in seg or seg in target_vertical.lower()):
                score += 5

            # Keyword matching
            combined = f"{title} {content} {cat}"
            for kw in keywords:
                if kw in combined:
                    score += 3
                if kw in title:
                    score += 2

            if score > 0:
                scored_records.append({
                    "id": row[0],
                    "segment": row[1],
                    "category": row[2],
                    "title": row[3],
                    "content": row[4],
                    "score": score
                })

        scored_records.sort(key=lambda x: x["score"], reverse=True)
        top_matches = scored_records[:max_entries]
        has_direct_match = bool(top_matches and top_matches[0]["score"] >= 5)

        return top_matches, has_direct_match


class PlivoBargeInController:
    """
    Coordinates real-time interruption (barge-in):
    When the customer starts speaking while AI audio is playing,
    immediately signals clearAudio to Plivo and cancels in-flight TTS & LLM.
    Guarantees strict single-voice output with zero voice overlap.
    """

    def __init__(self, plivo_ws):
        self.plivo_ws = plivo_ws
        self.is_ai_speaking = False
        self.is_interrupted = False
        self.active_tts_task = None
        self.active_llm_task = None
        self.active_speaking_tasks = set()
        self.active_turn_tasks = set()
        self.ai_speech_started_at = 0.0

    def register_speaking_task(self, task: asyncio.Task):
        """Register a task that plays audio out to Plivo."""
        self.active_tts_task = task
        self.active_speaking_tasks.add(task)
        self.ai_speech_started_at = time.time()
        task.add_done_callback(lambda t: self.active_speaking_tasks.discard(t))

    def register_turn_task(self, task: asyncio.Task):
        """Register a turn reasoning / LLM task."""
        self.active_llm_task = task
        self.active_turn_tasks.add(task)
        task.add_done_callback(lambda t: self.active_turn_tasks.discard(t))

    async def cancel_all_speech(self):
        """Immediately cancel all speech tasks and send clearAudio to Plivo."""
        self.is_ai_speaking = False
        self.is_interrupted = True

        # 1. Send clearAudio to Plivo WebSocket immediately
        if self.plivo_ws:
            try:
                await self.plivo_ws.send_text(json.dumps({"event": "clearAudio"}))
                logger.info("[BARGE-IN] ⚡ Sent clearAudio to Plivo")
            except Exception as e:
                logger.warning(f"[BARGE-IN] Failed to send clearAudio: {e}")

        # 2. Cancel all in-flight TTS / audio playback tasks (excluding caller task)
        curr = asyncio.current_task()
        if self.active_tts_task and self.active_tts_task != curr and not self.active_tts_task.done():
            self.active_tts_task.cancel()
            self.active_tts_task = None

        for task in list(self.active_speaking_tasks):
            if task != curr and not task.done():
                task.cancel()
        self.active_speaking_tasks = {t for t in self.active_speaking_tasks if t == curr}

        # 3. Cancel all in-flight turn / LLM generation tasks (excluding caller task)
        if self.active_llm_task and self.active_llm_task != curr and not self.active_llm_task.done():
            self.active_llm_task.cancel()
            self.active_llm_task = None

        for task in list(self.active_turn_tasks):
            if task != curr and not task.done():
                task.cancel()
        self.active_turn_tasks = {t for t in self.active_turn_tasks if t == curr}

    async def on_user_speech_detected(self):
        """Triggered when customer speech is detected while AI is speaking."""
        if not self.is_ai_speaking and not self.active_speaking_tasks and not self.active_tts_task:
            return
        # Acoustic feedback filter: require minimum 450ms playback duration before accepting barge-in
        if time.time() - getattr(self, "ai_speech_started_at", 0) < 0.45:
            return
        logger.info("[BARGE-IN] ⚡ Interruption detected! Cancelling active AI audio and holding.")
        await self.cancel_all_speech()


class ConversationalFillerEngine:
    """
    Provides ultra-low-latency conversational gap filler audio.
    Synthesizes and caches natural Indic/English verbal acknowledgments:
      - Telugu: "తప్పకుండా, మీకు ఇప్పుడే పూర్తి వివరాలు తెలియజేస్తాను."
      - Hindi (Male): "ज़रूर, मैं आपको अभी इसकी पूरी जानकारी देता हूँ."
      - Hindi (Female): "ज़रूर, मैं आपको अभी इसकी पूरी जानकारी देती हूँ."
      - English: "Sure, let me share these details with you right away."
    Streams immediately to Plivo while LLM reasons and retrieves catalogue knowledge.
    """
    _CACHE: Dict[Tuple[str, str], List[str]] = {}
    _LOCK: Optional[asyncio.Lock] = None

    FILLER_TEXTS: Dict[Tuple[str, str], str] = {
        ("te", "shubh"): "తప్పకుండా, మీకు ఇప్పుడే పూర్తి వివరాలు తెలియజేస్తాను.",
        ("te", "kavya"): "తప్పకుండా, మీకు ఇప్పుడే పూర్తి వివరాలు తెలియజేస్తాను.",
        ("hi", "shubh"): "ज़रूर, मैं आपको अभी इसकी पूरी जानकारी देता हूँ.",
        ("hi", "kavya"): "ज़रूर, मैं आपको अभी इसकी पूरी जानकारी देती हूँ.",
        ("en", "shubh"): "Sure, let me share these details with you right away.",
        ("en", "kavya"): "Sure, let me share these details with you right away.",
    }

    @classmethod
    def get_filler_text(cls, lang: str, speaker: str) -> str:
        clean_lang = "te" if "te" in (lang or "").lower() else ("hi" if "hi" in (lang or "").lower() else "en")
        clean_speaker = "shubh" if "shubh" in (speaker or "").lower() else "kavya"
        return cls.FILLER_TEXTS.get((clean_lang, clean_speaker), "తప్పకుండా, మీకు ఇప్పుడే పూర్తి వివరాలు తెలియజేస్తాను.")

    @classmethod
    async def get_or_synthesize_filler(cls, lang: str, speaker: str) -> List[str]:
        clean_lang = "te" if "te" in (lang or "").lower() else ("hi" if "hi" in (lang or "").lower() else "en")
        clean_speaker = "shubh" if "shubh" in (speaker or "").lower() else "kavya"
        cache_key = (clean_lang, clean_speaker)

        if cache_key in cls._CACHE and cls._CACHE[cache_key]:
            return cls._CACHE[cache_key]

        if cls._LOCK is None:
            cls._LOCK = asyncio.Lock()

        async with cls._LOCK:
            if cache_key in cls._CACHE and cls._CACHE[cache_key]:
                return cls._CACHE[cache_key]

            sarvam_lang = "te-IN" if clean_lang == "te" else ("hi-IN" if clean_lang == "hi" else "en-IN")
            text_phrase = cls.get_filler_text(clean_lang, clean_speaker)
            chunks: List[str] = []

            tts = SarvamStreamingTTSClient(
                language_code=sarvam_lang,
                speaker=clean_speaker,
                sample_rate=8000,
                output_codec="mulaw",
            )

            async def gen():
                yield text_phrase

            async def on_audio(b64: str):
                chunks.append(b64)

            try:
                await tts.synthesize_streaming(gen(), on_audio)
                if chunks:
                    cls._CACHE[cache_key] = chunks
                    logger.info(f"[FILLER] Cached {len(chunks)} chunks for {cache_key}")
            except Exception as e:
                logger.warning(f"[FILLER] Failed to synthesize filler for {cache_key}: {e}")

            return chunks

    @classmethod
    async def play_filler_chunk_stream(
        cls,
        lang: str,
        speaker: str,
        emit_func: Callable[[str], Any],
        is_interrupted_func: Callable[[], bool],
    ):
        """Streams filler audio chunks with small yield intervals allowing interruption."""
        chunks = await cls.get_or_synthesize_filler(lang, speaker)
        for chunk in chunks:
            if is_interrupted_func():
                break
            await emit_func(chunk)
            await asyncio.sleep(0.15)

