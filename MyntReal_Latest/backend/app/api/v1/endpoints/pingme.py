"""
VGK Assistant — AI Voice & Text Assistant Backend (DC Protocol)
DC_VGK_001: Stateless NLP endpoint powered by Gemini 2.0 Flash
Supports: English, Hindi, Telugu
Portals: Staff, Partner
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os, json, logging, re
from datetime import datetime, date, timedelta
import pytz

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.api.v1.endpoints.partner_auth import get_current_partner
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner
from app.models.staff_tasks import StaffTask, StaffDayPlan, StaffDayPlanItem, StaffTaskAssignee
from app.models.call_tracking import StaffCallLog as CallLog

router = APIRouter(prefix="/vgk", tags=["VGK Assistant"])

IST = pytz.timezone("Asia/Kolkata")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    f"{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"
)


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    role: str
    text: str

class VGKRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: List[ConversationTurn] = Field(default=[])
    language: str = Field(default="en", description="en | hi | te")
    company_id: Optional[int] = None
    allowed_intents: Optional[List[str]] = Field(default=None, description="Role-filtered intents from MENU_MASTER. None = all allowed.")
    accessible_routes: Optional[List[Dict[str, str]]] = Field(default=None, description="[{label, route}] pairs from frontend menu for navigate intent")

class VGKResponse(BaseModel):
    success: bool
    intent: str
    reply_text: str
    speak_text: str
    status: str
    options: List[Dict[str, str]] = []
    action_ready: bool = False
    action_type: Optional[str] = None
    resolved_data: Dict[str, Any] = {}
    employee_matches: List[Dict[str, str]] = []
    error: Optional[str] = None
    products: List[Dict[str, Any]] = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def now_ist():
    return datetime.now(IST)

def today_ist():
    return now_ist().date()

def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"

INTENT_MENU_CODES = {
    "create_task":           ["staff_task_tracker", "staff_tasks_assigned_by_me", "staff_tasks_assigned_to_me"],
    "create_lead":           ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "rvz_crm_leads"],
    "create_service_ticket": ["staff_service_queue", "staff_service_tickets", "service_queue"],
    "start_journey":         ["staff_my_journeys", "staff_all_journeys", "staff_vgk4u_journeys"],
    "end_journey":           ["staff_my_journeys", "staff_all_journeys", "staff_vgk4u_journeys"],
    "query_day_planner":     ["staff_day_planner"],
    "query_tasks":           ["staff_task_tracker", "staff_tasks_assigned_to_me", "staff_tasks_assigned_by_me"],
    "query_talk_time":       ["call_tracking_dashboard"],
    "marketplace_search":    ["staff_marketplace", "marketplace", "staff_zynova_po"],
    "query_crm_segment":     ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "staff_team_leads", "rvz_crm_leads"],
    "query_open_leads":      ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "staff_team_leads", "rvz_crm_leads"],
    "query_today_leads":     ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "staff_team_leads", "rvz_crm_leads"],
    "query_overdue_leads":   ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "staff_team_leads", "rvz_crm_leads"],
    "query_walkin_leads":    ["staff_crm_dashboard", "staff_leads", "staff_my_leads", "staff_team_leads", "rvz_crm_leads"],
    "edit_task":             ["staff_task_tracker", "staff_tasks_assigned_by_me"],
    "navigate":              [],
    "query_attendance":      [],
    "query_kra":             ["staff_kra", "staff_my_kra", "staff_kra_dashboard"],
    "log_call":              ["call_tracking_dashboard", "staff_my_leads", "staff_crm_dashboard"],
    "general_help":          [],
}

def _allowed_staff_intents(allowed_intents: Optional[List[str]]) -> List[str]:
    if not allowed_intents:
        return list(INTENT_MENU_CODES.keys())
    allowed_set = set(allowed_intents)
    result = ["general_help"]
    for intent, codes in INTENT_MENU_CODES.items():
        if not codes or any(c in allowed_set for c in codes):
            result.append(intent)
    return result


def _build_system_prompt(portal_type: str, user_name: str, emp_code: str,
                          today_str: str, language: str,
                          allowed_intents: Optional[List[str]] = None,
                          accessible_routes: Optional[List[Dict[str, str]]] = None) -> str:
    lang_instruction = {
        "en": "Always respond in English.",
        "hi": "Always respond in Hindi (Devanagari script). If the user switches to English, respond in English.",
        "te": "Always respond in Telugu script. Voice input may arrive in English phonetics — understand it and respond in Telugu.",
    }.get(language, "Detect user language and respond in the same language (English, Hindi, or Telugu).")

    ALL_INTENT_DEFS = {
        "create_task":           "- create_task           : Assign/create a task or activity. Required: title, assigned_to_name, due_date (ISO YYYY-MM-DD), priority (low/medium/high/critical)",
        "create_lead":           "- create_lead           : Add a new CRM lead. Required: lead_name, phone, category (EV/Real Estate/Insurance/General)",
        "create_service_ticket": "- create_service_ticket : Raise a service/support ticket. Required: customer_name, phone, issue_description, ticket_type (spares/technical/general)",
        "start_journey":         "- start_journey         : Start a GPS journey/field visit. Required: company_name (select from list)",
        "end_journey":           "- end_journey           : End the current active GPS journey",
        "marketplace_search":    "- marketplace_search    : Search VGK4U spare parts catalog. Required: search_query",
        "query_crm_segment":     "- query_crm_segment     : Show CRM leads for a specific segment/category (Real Dreams, EV Spares, Insurance, Solar, ETC Training, Finance, General). Required: segment_name",
        "query_open_leads":      "- query_open_leads      : Show all open/new/pending CRM leads. No fields required.",
        "query_today_leads":     "- query_today_leads     : Show CRM leads with follow-up scheduled for today. No fields required.",
        "query_overdue_leads":   "- query_overdue_leads   : Show overdue/missed CRM leads (past their follow-up date and not closed). No fields required.",
        "query_walkin_leads":    "- query_walkin_leads    : Show walk-in type CRM leads from the showroom. No fields required.",
        "query_day_planner":     "- query_day_planner     : Show today's day plan and task progress",
        "query_tasks":           "- query_tasks           : Show pending/priority tasks assigned to the user",
        "query_talk_time":       "- query_talk_time       : Show today's call statistics and talk time",
        "edit_task":              "- edit_task              : Edit an existing task. Required: task_code or partial title, field_to_edit, new_value",
        "navigate":              "- navigate               : Open/go to any page or module. E.g., 'go to CRM', 'open service queue', 'show my journeys'. Set resolved_data.route to the matching path.",
        "query_attendance":      "- query_attendance       : Check today's attendance status, check-in time, worked hours, GPS status.",
        "query_kra":             "- query_kra              : Check KRA (Key Result Area) performance targets and current status.",
        "log_call":              "- log_call               : Log a call quickly. Required: contact_name, phone, duration_minutes, outcome (connected/not_answered/callback_requested)",
        "create_walkin":         "- create_walkin          : Record a new customer walk-in visit at your showroom. Required: customer_name, phone, visit_purpose (general/ev/real_estate/insurance/solar)",
        "query_partner_activity": "- query_partner_activity : Show today's followups and pending activities — CRM leads due today, walkins needing followup.",
        "general_help":          "- general_help           : Help user understand VGK Assistant capabilities or answer general questions.",
    }
    PARTNER_INTENTS = {
        "create_lead", "create_service_ticket", "navigate", "general_help",
        "create_walkin", "query_partner_activity", "marketplace_search",
    }

    if portal_type == "partner":
        active_intents = PARTNER_INTENTS
    else:
        active_set = set(_allowed_staff_intents(allowed_intents))
        active_intents = active_set

    intent_lines = "\n".join(v for k, v in ALL_INTENT_DEFS.items() if k in active_intents)
    valid_keys = "|".join(k for k in ALL_INTENT_DEFS if k in active_intents) + "|clarify|unknown"
    intents = f"AVAILABLE INTENTS (you may ONLY suggest these — respect user role):\n{intent_lines}"

    nav_section = ""
    if accessible_routes and "navigate" in active_intents:
        route_lines = "\n".join(f"  - {r['label']}: {r['route']}" for r in accessible_routes[:40])
        nav_section = f"\nACCESSIBLE PAGES (for navigate intent — use exact route value in resolved_data.route):\n{route_lines}"

    if portal_type == "partner":
        _flow_label = "create_walkin — follow this exactly"
        _flow_body = (
            "Turn 1 -> user: 'create walkin' -> ask: 'What is the customer name?'"
            " Turn 2 -> user: 'Ravi Kumar' -> intent=create_walkin, ask: 'What is their phone number?'"
            " Turn 3 -> user: '9876543210' -> intent=create_walkin, ask: 'What is the visit purpose? (general / ev / real_estate / insurance / solar)'"
            " Turn 4 -> user: 'EV' -> intent=create_walkin, action_ready=true, status=confirming, summarise all fields."
        )
    else:
        _flow_label = "create_task — follow this exactly"
        _flow_body = (
            "Turn 1 -> user: 'create task' -> ask: 'What is the task title?'"
            " Turn 2 -> user: 'Fix billing issue' -> intent=create_task, ask: 'Who should I assign this to?'"
            " Turn 3 -> user: 'Ramesh' -> intent=create_task, set fuzzy_lookup={field:assigned_to_name,query:Ramesh}, ask: 'What is the due date?'"
            " Turn 4 -> user: 'tomorrow' -> intent=create_task, ask: 'What priority? low / medium / high / critical'"
            " Turn 5 -> user: 'high' -> intent=create_task, action_ready=true, status=confirming, summarise all fields."
        )

    return f"""You are VGK Assistant — a friendly, smart AI assistant for the MNR/VGK4U staff platform.
{lang_instruction}

Today: {today_str}. User: {user_name} ({emp_code}). Portal: {portal_type}.

{intents}{nav_section}

RESPONSE RULES:
1. ALWAYS respond with VALID JSON ONLY — no text outside JSON, no markdown code blocks.
2. INTENT LOCK (CRITICAL): Look at the last assistant message in conversation history. If it was asking for a specific field (title, name, date, priority, phone, etc.), the user's current reply is the answer to THAT question — keep the SAME intent. Only switch intent if the user explicitly says "cancel", "stop", "instead", or starts a completely new request. A name, a date, a number, or a short phrase is NEVER a new intent — it is always an answer to the previous question.
3. If intent is unclear on the VERY FIRST message with no history → set intent="clarify", provide 2-5 helpful options[].
4. Collect fields ONE at a time. Never ask multiple questions in one reply.
5. When ALL required fields are collected → set action_ready=true, status="confirming", write a clear summary in reply_text.
6. NAMES — FUZZY LOOKUP REQUIRED (CRITICAL): For ANY name field (assigned_to_name, customer_name, lead_name) you MUST set fuzzy_lookup. NEVER put the raw name string into resolved_data — the backend must validate names against the real database. Example: user says "Sai Kumar" when asked for assignee → set fuzzy_lookup={{"field":"assigned_to_name","query":"Sai Kumar"}} and leave resolved_data.assigned_to_name EMPTY. The backend fills it after DB lookup.
7. Dates: convert natural language to ISO ("tomorrow" → {(today_ist() + timedelta(days=1)).isoformat()}, "next Monday" → calculate correctly).
8. Be warm, brief, guiding. Max 2 sentences in reply_text.
9. If user says something unclear → guide them with suggestions, never fail silently.
10. For edit_task: first ask which task, then what to change.
11. speak_text should be ≤25 words (for text-to-speech).
12. FLOW EXAMPLE ({_flow_label}):
    {_flow_body}

RESPONSE FORMAT (strict JSON):
{{
  "intent": "{valid_keys}",
  "reply_text": "Friendly conversational reply shown to user",
  "speak_text": "Brief version for TTS, max 25 words",
  "status": "collecting|confirming|done|error",
  "options": [{{"label": "Display Text", "value": "machine_value"}}],
  "action_ready": false,
  "missing_fields": ["field1"],
  "next_field": "next_field_to_collect",
  "fuzzy_lookup": {{"field": "assigned_to_name", "query": "spoken_name"}},
  "resolved_data": {{}}
}}"""


async def _call_gemini(system_prompt: str, conversation: List[Dict]) -> Dict:
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="GOOGLE_API_KEY not configured")

    contents = [{"role": "user", "parts": [{"text": system_prompt}]},
                {"role": "model", "parts": [{"text": '{"intent":"general_help","reply_text":"Ready to help!","speak_text":"Ready to help!","status":"collecting","options":[],"action_ready":false,"missing_fields":[],"next_field":"","fuzzy_lookup":null,"resolved_data":{}}'}]}]

    for turn in conversation:
        role = "user" if turn["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn["text"]}]})

    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 512}
    }

    try:
        import httpx as _httpx
    except ImportError:
        raise HTTPException(status_code=503, detail="VGK Assistant AI service is not available on this server.")
    async with _httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(GEMINI_URL, json=payload)
        if resp.status_code != 200:
            err_text = resp.text[:500]
            logger.error(f"[VGK] Gemini {resp.status_code} from {GEMINI_MODEL}: {err_text}")
            if resp.status_code == 400 and "API_KEY_INVALID" in err_text:
                raise HTTPException(status_code=503, detail="VGK Assistant is not configured. Contact your administrator.")
            if resp.status_code in (403, 429) and "SERVICE_DISABLED" in err_text:
                raise HTTPException(status_code=503, detail="VGK Assistant AI service is currently unavailable. Contact your administrator to enable the Generative Language API.")
            raise HTTPException(status_code=503, detail=f"VGK Assistant is temporarily unavailable. Please try again shortly.")
        data = resp.json()

    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        return json.loads(raw)
    except Exception:
        return {
            "intent": "unknown",
            "reply_text": "I didn't quite understand. Could you rephrase that?",
            "speak_text": "Could you rephrase that?",
            "status": "collecting", "options": [], "action_ready": False,
            "missing_fields": [], "next_field": "", "fuzzy_lookup": None, "resolved_data": {}
        }


def _fuzzy_employees(query: str, db: Session) -> List[Dict]:
    pattern = f"%{query}%"
    emps = db.query(StaffEmployee).filter(
        StaffEmployee.status == "active",
        or_(
            StaffEmployee.full_name.ilike(pattern),
            StaffEmployee.emp_code.ilike(pattern)
        )
    ).limit(5).all()
    return [{"label": f"{e.full_name} ({e.emp_code})", "value": str(e.id),
             "name": e.full_name, "emp_code": e.emp_code} for e in emps]


def _query_day_planner(employee_id: int, db: Session, language: str) -> Dict:
    today = today_ist()
    plan = db.query(StaffDayPlan).filter(
        StaffDayPlan.employee_id == employee_id,
        StaffDayPlan.plan_date == today
    ).first()

    if not plan:
        msgs = {
            "en": "You don't have a day plan set for today. Visit the Task Planner to create one!",
            "hi": "आज के लिए कोई दिन योजना नहीं है। Task Planner पर जाकर बनाएं!",
            "te": "ఈరోజు మీకు డే ప్లాన్ లేదు. Task Planner కి వెళ్ళి ఒకటి సృష్టించండి!"
        }
        txt = msgs.get(language, msgs["en"])
        return {"reply_text": txt, "speak_text": txt}

    labels = {
        "en": f"Today's plan has {plan.total_planned} items — {plan.total_completed} completed, {plan.total_in_progress} in progress, {plan.total_pending} pending.",
        "hi": f"आज की योजना में {plan.total_planned} कार्य हैं — {plan.total_completed} पूर्ण, {plan.total_in_progress} चल रहे, {plan.total_pending} बाकी।",
        "te": f"నేడు మీ ప్లాన్‌లో {plan.total_planned} పనులు ఉన్నాయి — {plan.total_completed} పూర్తయ్యాయి, {plan.total_in_progress} జరుగుతున్నాయి, {plan.total_pending} పెండింగ్‌లో ఉన్నాయి."
    }
    top_items = []
    if plan.items:
        for item in plan.items[:3]:
            if item.task:
                top_items.append(f"• {item.task.title[:40]}")

    txt = labels.get(language, labels["en"])
    if top_items:
        txt += " Top items: " + "; ".join(top_items)
    speak = labels.get(language, labels["en"])
    return {"reply_text": txt, "speak_text": speak}


def _query_tasks(employee_id: int, db: Session, language: str) -> Dict:
    tasks = db.query(StaffTask).filter(
        StaffTask.primary_assignee_id == employee_id,
        StaffTask.status.in_(["pending", "in_progress", "on_hold"])
    ).order_by(
        desc(StaffTask.priority == "critical"),
        desc(StaffTask.priority == "high"),
        StaffTask.due_date
    ).limit(5).all()

    if not tasks:
        msgs = {
            "en": "Great news — you have no pending tasks right now!",
            "hi": "बढ़िया! अभी आपके पास कोई लंबित कार्य नहीं है।",
            "te": "మంచి వార్త — ఇప్పుడు మీకు పెండింగ్ పనులు లేవు!"
        }
        txt = msgs.get(language, msgs["en"])
        return {"reply_text": txt, "speak_text": txt}

    lines = []
    for t in tasks:
        due = f" (due {t.due_date.strftime('%d %b')})" if t.due_date else ""
        lines.append(f"• [{t.priority.upper()}] {t.title[:35]}{due}")

    hdrs = {
        "en": f"You have {len(tasks)} active tasks:",
        "hi": f"आपके {len(tasks)} सक्रिय कार्य हैं:",
        "te": f"మీకు {len(tasks)} చురుకైన పనులు ఉన్నాయి:"
    }
    txt = hdrs.get(language, hdrs["en"]) + " " + "; ".join(lines)
    speak = hdrs.get(language, hdrs["en"]) + f" Top: {tasks[0].title[:30]}"
    return {"reply_text": txt, "speak_text": speak}


def _query_talk_time(employee_id: int, db: Session, language: str) -> Dict:
    today_str = today_ist().strftime("%Y-%m-%d")
    logs = db.query(CallLog).filter(
        CallLog.staff_id == employee_id,
        CallLog.call_date == today_str
    ).all()

    if not logs:
        msgs = {
            "en": "No calls recorded today yet.",
            "hi": "आज अभी तक कोई कॉल दर्ज नहीं हुई।",
            "te": "ఈరోజు ఇంకా కాల్స్ రికార్డ్ కాలేదు."
        }
        txt = msgs.get(language, msgs["en"])
        return {"reply_text": txt, "speak_text": txt}

    total = len(logs)
    total_sec = sum(l.duration_seconds or 0 for l in logs)
    outgoing = sum(1 for l in logs if (l.call_type or "").lower() in ("outgoing", "out"))
    incoming = sum(1 for l in logs if (l.call_type or "").lower() in ("incoming", "in"))
    missed = total - outgoing - incoming

    labels = {
        "en": f"Today: {total} calls, talk time {format_duration(total_sec)} — {outgoing} outgoing, {incoming} incoming, {missed} missed.",
        "hi": f"आज: {total} कॉल, बात का समय {format_duration(total_sec)} — {outgoing} आउटगोइंग, {incoming} इनकमिंग, {missed} मिस्ड।",
        "te": f"ఈరోజు: {total} కాల్స్, మాటల సమయం {format_duration(total_sec)} — {outgoing} అవుట్‌గోయింగ్, {incoming} ఇన్‌కమింగ్, {missed} మిస్డ్."
    }
    txt = labels.get(language, labels["en"])
    return {"reply_text": txt, "speak_text": txt}


# ═══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK ENGINE — DC Protocol
# Active when Gemini API is unavailable. Handles all intents via keyword + state.
# ═══════════════════════════════════════════════════════════════════════════════

_RB_KEYWORDS: Dict[str, List[str]] = {
    "end_journey":           ["end journey", "stop journey", "finish journey", "complete journey", "end my journey", "journey end", "stop tracking"],
    "start_journey":         ["start journey", "begin journey", "start tracking", "start my journey", "journey start", "new journey", "go for journey"],
    "create_task":           ["create task", "new task", "assign task", "add task", "make task", "create activity", "can you create activity", "aquatic", "create a task", "assign a task"],
    "create_lead":           ["create lead", "new lead", "add lead", "add contact", "new contact", "create contact", "lead for"],
    "create_service_ticket": ["create ticket", "new ticket", "raise ticket", "service ticket", "technical ticket", "raise a ticket", "log ticket", "raise complaint", "open ticket"],
    "query_day_planner":     ["day plan", "my plan", "today plan", "progress today", "day planner", "show plan", "what is my plan", "show my plan", "daily plan"],
    "query_tasks":           ["my tasks", "pending task", "show tasks", "task list", "open task", "active tasks", "list tasks", "show my tasks", "what tasks"],
    "query_talk_time":       ["talk time", "call stats", "my calls", "calls today", "call time", "call log", "call count", "how many calls"],
    "marketplace_search":    [
        "search product", "search spare", "find spare", "find part", "search catalog",
        "spare part", "product search", "search market",
        "spare catalog", "availability", "in stock", "price of", "cost of",
        "charger", "battery", "motor", "tyre", "tire", "brake", "mirror", "controller",
        "headlight", "tail light", "horn", "seat", "handle", "cable", "bearing",
    ],
    "query_crm_segment":     [
        "real dreams", "real estate leads", "real estate", "property leads",
        "ev leads", "ev spares leads", "electric vehicle leads", "ev segment",
        "insurance leads", "insurance segment",
        "solar leads", "solar segment",
        "etc leads", "etc training", "training leads", "training segment",
        "finance leads", "finance segment",
        "general leads", "all leads", "show leads", "crm leads",
        "show real", "show insurance", "show solar", "show ev", "show training",
    ],
    "query_open_leads":      [
        "open leads", "new leads", "pending leads", "show open leads", "open crm",
        "unassigned leads", "fresh leads", "status open", "leads not closed",
        "show new leads", "view open leads", "my open leads", "active leads",
    ],
    "query_today_leads":     [
        "today leads", "today's leads", "today followup leads", "leads today",
        "follow up today leads", "today crm", "due today", "leads due today",
        "show today leads", "today's followup", "scheduled today",
    ],
    "query_overdue_leads":   [
        "overdue leads", "missed leads", "expired leads", "overdue followup",
        "leads overdue", "past due leads", "missed followup leads",
        "show overdue", "overdue crm", "leads not followed up", "lapsed leads",
    ],
    "query_walkin_leads":    [
        "walkin leads", "walk-in leads", "walk in leads", "walkins", "walk-ins",
        "show walkins", "walk in crm", "walk in customers", "showroom leads",
        "show walk in leads", "walkin crm leads",
    ],
    "general_help":          ["help", "what can you do", "capabilities", "what are you", "hi", "hello", "hey vgk", "namaste"],
    "create_walkin":         ["create walkin", "new walkin", "add walkin", "walk in customer", "walkin customer",
                              "new walk in", "add walk in", "register walkin", "walkin entry", "customer visit",
                              "new visitor", "log walkin", "record walkin", "register customer", "walk-in",
                              "create a walkin", "register a walkin", "add a walkin", "log a walkin",
                              "new walk-in", "create walk-in", "register walk-in"],
    "query_partner_activity": ["today followup", "today's followup", "todays followup", "my followup",
                               "follow up today", "pending followup", "followup list", "followups today",
                               "my activity", "partner activity", "what to follow", "follow up list",
                               "my leads today", "pending leads", "today activity", "daily followup",
                               "followup today", "what's pending"],
}


_PORTAL_ALLOWED_INTENTS: Dict[str, set] = {
    "staff":       set(),  # empty = all allowed
    "partner":     {"create_lead", "create_service_ticket", "navigate", "general_help",
                    "create_walkin", "query_partner_activity", "marketplace_search"},
    "marketplace": {"marketplace_search", "general_help"},
}


def _rb_detect_intent(msg_lower: str, conversation_history: List[ConversationTurn],
                      portal_type: str = "staff") -> str:
    allowed = _PORTAL_ALLOWED_INTENTS.get(portal_type, set())

    def _allowed(intent: str) -> bool:
        return not allowed or intent in allowed

    # DC: Check CURRENT message first — prevents history bleeding
    for intent, kws in _RB_KEYWORDS.items():
        if _allowed(intent) and any(kw in msg_lower for kw in kws):
            return intent
    # Fall back to most recent history turn only if current message has no match
    for turn in reversed(conversation_history):
        if turn.role == "user":
            tl = turn.text.lower()
            for intent, kws in _RB_KEYWORDS.items():
                if _allowed(intent) and any(kw in tl for kw in kws):
                    return intent
            break  # Only check the last user turn
    if portal_type == "marketplace":
        return "marketplace_search"
    return "general_help"


def _rb_pairs(conversation_history: List[ConversationTurn], current_msg: str) -> List[tuple]:
    """Return (question_lower, user_answer) pairs from history + current message."""
    pairs: List[tuple] = []
    first_asst = False
    hist = [{"role": t.role, "text": t.text} for t in conversation_history]
    for i, turn in enumerate(hist):
        if turn["role"] == "assistant":
            first_asst = True
        elif turn["role"] == "user" and first_asst:
            q = hist[i - 1]["text"].lower() if i > 0 and hist[i - 1]["role"] == "assistant" else ""
            pairs.append((q, turn["text"].strip()))
    if first_asst:
        last_q = next((t["text"].lower() for t in reversed(hist) if t["role"] == "assistant"), "")
        pairs.append((last_q, current_msg))
    return pairs


def _rb_parse_date(text: str) -> str:
    today = today_ist()
    tl = text.lower().strip()
    if tl in ("today",):        return today.isoformat()
    if tl in ("tomorrow", "tmrw", "tmr", "tom"):  return (today + timedelta(days=1)).isoformat()
    if "next week" in tl:  return (today + timedelta(days=7)).isoformat()
    if "next month" in tl: return (today + timedelta(days=30)).isoformat()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", tl)
    if m: return text.strip()
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?$", tl)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else today.year
        if yr < 100: yr += 2000
        try:
            from datetime import date as _date
            return _date(yr, mo, d).isoformat()
        except Exception:
            pass
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    for abbr, num in months.items():
        for pat in [rf"(\d{{1,2}})\s*{abbr}", rf"{abbr}\s*(\d{{1,2}})"]:
            m2 = re.search(pat, tl)
            if m2:
                try:
                    from datetime import date as _date
                    dt = _date(today.year, num, int(m2.group(1)))
                    if dt < today: dt = _date(today.year + 1, num, int(m2.group(1)))
                    return dt.isoformat()
                except Exception:
                    pass
    return text.strip()



# ── Localised reply strings ────────────────────────────────────────────────────
_LANG_RESP = {
    "te": {
        "found":      u"\U0001F50D '{}' \u0c15\u0c4b\u0c38\u0c02 {} \u0c2b\u0c32\u0c3f\u0c24\u0c3e\u0c32\u0c41:\n",
        "not_found":  u"'{}' \u0c15\u0c3f \u0c38\u0c30\u0c3f\u0c2a\u0c4b\u0c32\u0c47 \u0c09\u0c24\u0c4d\u0c2a\u0c24\u0c4d\u0c24\u0c41\u0c32\u0c41 \u0c32\u0c47\u0c35\u0c41. \u0c35\u0c47\u0c30\u0c47 \u0c2a\u0c26\u0c02 \u0c2a\u0c4d\u0c30\u0c2f\u0c24\u0c4d\u0c28\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f.",
        "what":       u"\u0c2e\u0c40\u0c30\u0c41 \u0c0f \u0c38\u0c4d\u0c2a\u0c47\u0c30\u0c4d \u0c2a\u0c3e\u0c30\u0c4d\u0c1f\u0c4d \u0c35\u0c46\u0c24\u0c41\u0c15\u0c41\u0c24\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c30\u0c41?",
        "nearby":     u"'{}' \u0c15\u0c3f \u0c38\u0c30\u0c3f\u0c2a\u0c4b\u0c32\u0c47\u0c35\u0c3f \u0c32\u0c47\u0c35\u0c41. '{}' \u0c15\u0c4b\u0c38\u0c02 \u0c26\u0c17\u0c4d\u0c17\u0c30\u0c3f \u0c2b\u0c32\u0c3f\u0c24\u0c3e\u0c32\u0c41:\n",
        "interested": u"'{}' \u0c15\u0c3f \u0c38\u0c30\u0c3f\u0c2a\u0c4b\u0c32\u0c47\u0c35\u0c3f \u0c32\u0c47\u0c35\u0c41. \u0c07\u0c35\u0c3f \u0c2e\u0c40\u0c15\u0c41 \u0c09\u0c2a\u0c2f\u0c4b\u0c17\u0c2a\u0c21\u0c35\u0c1a\u0c4d\u0c1a\u0c41:\n",
        "failed":     u"\u0c36\u0c4b\u0c27\u0c28 \u0c35\u0c3f\u0c2b\u0c32\u0c2e\u0c48\u0c02\u0c26\u0c3f. \u0c26\u0c2f\u0c1a\u0c47\u0c38\u0c3f \u0c2e\u0c33\u0c4d\u0c33\u0c40 \u0c2a\u0c4d\u0c30\u0c2f\u0c24\u0c4d\u0c28\u0c3f\u0c02\u0c1a\u0c02\u0c21\u0c3f.",
    },
    "hi": {
        "found":      u"\U0001F50D '{}' \u0915\u0947 \u0932\u093f\u090f {} \u092a\u0930\u093f\u0923\u093e\u092e:\n",
        "not_found":  u"'{}' \u0915\u0947 \u0932\u093f\u090f \u0915\u094b\u0908 \u0909\u0924\u094d\u092a\u093e\u0926 \u0928\u0939\u0940\u0902 \u092e\u093f\u0932\u093e\u0964",
        "what":       u"\u0906\u092a \u0915\u094c\u0928 \u0938\u093e \u0938\u094d\u092a\u0947\u092f\u0930 \u092a\u093e\u0930\u094d\u091f \u0916\u094b\u091c \u0930\u0939\u0947 \u0939\u0948\u0902?",
        "nearby":     u"'{}' \u0915\u093e \u0915\u094b\u0908 \u092e\u093f\u0932\u093e\u0928 \u0928\u0939\u0940\u0902\u0964 '{}' \u0915\u0947 \u0915\u0930\u0940\u092c\u0940 \u092a\u0930\u093f\u0923\u093e\u092e:\n",
        "interested": u"'{}' \u0915\u093e \u0915\u094b\u0908 \u092e\u093f\u0932\u093e\u0928 \u0928\u0939\u0940\u0902\u0964 \u0936\u093e\u092f\u0926 \u092f\u0947 \u0915\u093e\u092e \u0906\u090f\u0902:\n",
        "failed":     u"\u0916\u094b\u091c \u0935\u093f\u092b\u0932 \u0930\u0939\u0940\u0964 \u0915\u0943\u092a\u092f\u093e \u092a\u0941\u0928\u0903 \u092a\u094d\u0930\u092f\u093e\u0938 \u0915\u0930\u0947\u0902\u0964",
    },
}

# Telugu / transliterated keywords → English search term
_TELUGU_KEYWORDS = {
    "బ్యాటరీ": "battery", "బ్యాటరీలు": "battery", "battery": "battery",
    "చార్జర్": "charger", "charger": "charger", "చార్జర్లు": "charger",
    "మోటార్": "motor", "మోటర్": "motor",
    "టైర్": "tyre", "tyre": "tyre", "tire": "tire",
    "బ్రేక్": "brake", "brake": "brake",
    "మిర్రర్": "mirror", "mirror": "mirror",
    "కంట్రోలర్": "controller", "controller": "controller",
    "హెడ్‌లైట్": "headlight", "headlight": "headlight",
    "హెడ్లైట్": "headlight",
    "హార్న్": "horn", "horn": "horn",
    "కేబుల్": "cable", "cable": "cable",
    "బేరింగ్": "bearing", "bearing": "bearing",
    "స్విచ్": "switch", "switch": "switch",
    "లాక్": "lock", "lock": "lock",
    "సీట్": "seat", "seat": "seat",
    "డిస్‌ప్లే": "display", "display": "display",
    "ఫోర్క్": "fork", "fork": "fork",
    "ఇండికేటర్": "indicator", "indicator": "indicator",
    "బల్బ్": "bulb", "bulb": "bulb",
    "సెన్సర్": "sensor", "sensor": "sensor",
    "కవర్": "cover", "cover": "cover",
    "గ్లాస్": "glass", "glass": "glass",
    "స్ప్రోకెట్": "sprocket", "sprocket": "sprocket",
    "షాకర్": "shocker", "shocker": "shocker",
    "మడ్‌గార్డ్": "mudguard", "mudguard": "mudguard",
    "మిరర్": "mirror",
}

def _L(lang: str, key: str, *args) -> str:
    """Get a localised string; fall back to English built-in."""
    tmpl = _LANG_RESP.get(lang, {}).get(key)
    if tmpl and args:
        return tmpl.format(*args)
    return tmpl or ""

def _map_telugu_query(query: str) -> str:
    """If query contains Telugu keywords, map to English equivalent."""
    words = query.strip().split()
    mapped = []
    for w in words:
        mapped.append(_TELUGU_KEYWORDS.get(w, _TELUGU_KEYWORDS.get(w.lower(), w)))
    return " ".join(mapped)

def _rb_resp(intent: str, reply: str, speak: str = "", status: str = "collecting",
             options: List = None, action_ready: bool = False, resolved: Dict = None,
             emp_matches: List = None) -> Dict:
    return {
        "intent": intent, "reply_text": reply,
        "speak_text": (speak or reply)[:120],
        "status": status, "options": options or [],
        "action_ready": action_ready, "missing_fields": [],
        "next_field": "", "fuzzy_lookup": None,
        "resolved_data": resolved or {}, "employee_matches": emp_matches or [],
    }


def _rb_create_task(msg: str, pairs: List[tuple], employee_id: Optional[int], db: Session) -> Dict:
    fi = len(pairs)
    if fi == 0:
        return _rb_resp("create_task", "What's the title of the task?", "What is the task title?")
    if fi == 1:
        title = pairs[0][1]
        matches = _fuzzy_employees(msg, db) if employee_id else []
        if len(matches) == 1:
            return _rb_resp("create_task",
                f"Assigning to {matches[0]['name']}. What's the due date? (e.g. tomorrow, 5 Mar)",
                "What is the due date?",
                resolved={"title": title, "primary_assignee_id": int(matches[0]["value"]), "assignee_name": matches[0]["name"]})
        if len(matches) > 1:
            opts = [{"label": m["label"], "value": m["value"]} for m in matches]
            return _rb_resp("create_task", f"Found {len(matches)} people. Which one?", "Which person?",
                            options=opts, resolved={"title": title}, emp_matches=matches)
        return _rb_resp("create_task",
            f"No staff found for '{msg}'. Please try a different name or employee code.",
            "Staff not found.", resolved={"title": title})
    if fi == 2:
        title = pairs[0][1]
        assignee_ans = pairs[1][1]
        assignee_id, assignee_name = None, assignee_ans
        if assignee_ans.isdigit():
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == int(assignee_ans)).first()
            if emp: assignee_id, assignee_name = emp.id, emp.full_name
        else:
            m = _fuzzy_employees(assignee_ans, db)
            if m: assignee_id, assignee_name = int(m[0]["value"]), m[0]["name"]
        due = _rb_parse_date(msg)
        return _rb_resp("create_task",
            f"Due date: {due}. What's the priority? (low / medium / high / critical)", "What is the priority?",
            resolved={"title": title, "primary_assignee_id": assignee_id, "assignee_name": assignee_name, "due_date": due})
    if fi >= 3:
        title = pairs[0][1]
        assignee_ans = pairs[1][1]
        assignee_id, assignee_name = None, assignee_ans
        if assignee_ans.isdigit():
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == int(assignee_ans)).first()
            if emp: assignee_id, assignee_name = emp.id, emp.full_name
        else:
            m = _fuzzy_employees(assignee_ans, db)
            if m: assignee_id, assignee_name = int(m[0]["value"]), m[0]["name"]
        due = _rb_parse_date(pairs[2][1])
        pri = msg.lower().strip()
        if pri not in ("low", "medium", "high", "critical"): pri = "medium"
        summary = (f"📋 Create Task\n"
                   f"Title: {title}\nAssign To: {assignee_name}\n"
                   f"Due: {due}\nPriority: {pri.upper()}\n\nConfirm?")
        return _rb_resp("create_task", summary, f"Task for {assignee_name}, priority {pri}",
                        status="confirming", action_ready=True,
                        resolved={"title": title, "primary_assignee_id": assignee_id,
                                  "assignee_name": assignee_name, "due_date": due, "priority": pri})
    return _rb_resp("create_task", "What's the task title?")


def _rb_create_lead(msg: str, pairs: List[tuple]) -> Dict:
    fi = len(pairs)
    if fi == 0:
        return _rb_resp("create_lead", "What's the lead's full name?", "What is the lead name?")
    if fi == 1:
        name = pairs[0][1]
        return _rb_resp("create_lead", f"Got it — {name}. What's their phone number?", "Phone number?",
                        resolved={"name": name, "lead_name": name})
    name, phone = pairs[0][1], pairs[1][1]
    summary = f"📋 New Lead\nName: {name}\nPhone: {phone}\n\nConfirm?"
    return _rb_resp("create_lead", summary, f"Lead ready for {name}",
                    status="confirming", action_ready=True,
                    resolved={"name": name, "lead_name": name, "phone": phone})


def _rb_create_ticket(msg: str, pairs: List[tuple]) -> Dict:
    fi = len(pairs)
    if fi == 0:
        return _rb_resp("create_service_ticket", "What's the customer's name?", "Customer name?")
    if fi == 1:
        cname = pairs[0][1]
        return _rb_resp("create_service_ticket", f"Got it — {cname}. What's their phone number?", "Phone number?",
                        resolved={"customer_name": cname})
    if fi == 2:
        cname, phone = pairs[0][1], pairs[1][1]
        return _rb_resp("create_service_ticket",
            f"Phone: {phone}. Please briefly describe the issue:", "Describe the issue.",
            resolved={"customer_name": cname, "customer_phone": phone})
    cname, phone, issue = pairs[0][1], pairs[1][1], pairs[2][1]
    summary = f"📋 Service Ticket\nCustomer: {cname}\nPhone: {phone}\nIssue: {issue[:80]}\n\nConfirm?"
    return _rb_resp("create_service_ticket", summary, f"Ticket ready for {cname}",
                    status="confirming", action_ready=True,
                    resolved={"customer_name": cname, "customer_phone": phone,
                              "issue_description": issue, "issue_category": "General Complaint", "ticket_type": "general"})


def _rb_start_journey(pairs: List[tuple], db: Session) -> Dict:
    try:
        from app.models.staff_accounts import AssociatedCompany
        companies = db.query(AssociatedCompany).filter(
            AssociatedCompany.is_active == True
        ).order_by(AssociatedCompany.company_name).limit(10).all()
        fi = len(pairs)
        if fi == 0:
            if not companies:
                return _rb_resp("start_journey", "No companies configured. Contact your administrator.", status="done")
            opts = [{"label": c.company_name, "value": str(c.id)} for c in companies]
            return _rb_resp("start_journey", "Which company are you travelling for?", "Select company.", options=opts)
        sel = pairs[0][1].strip()
        company = next((c for c in companies if str(c.id) == sel), None)
        if not company:
            company = next((c for c in companies if c.company_name.lower() == sel.lower()), None)
        if not company and companies:
            company = companies[0]
        summary = f"📍 Start Journey\nCompany: {company.company_name}\n\nConfirm to begin GPS tracking."
        return _rb_resp("start_journey", summary, f"Start journey for {company.company_name}?",
                        status="confirming", action_ready=True,
                        resolved={"company_id": company.id, "company_name": company.company_name})
    except Exception as e:
        logger.error(f"[VGK-RB] start_journey error: {e}")
        return _rb_resp("start_journey", "Unable to load company list. Please use the Journey page.", status="done")


def _rb_end_journey(employee_id: Optional[int], db: Session) -> Dict:
    if not employee_id:
        return _rb_resp("end_journey", "Journey tracking is not available for this portal.", status="done")
    try:
        from app.models.staff_journey import StaffJourney, JourneyStatus
        journey = db.query(StaffJourney).filter(
            StaffJourney.employee_id == employee_id,
            StaffJourney.status == JourneyStatus.IN_PROGRESS
        ).first()
        if not journey:
            return _rb_resp("end_journey", "You don't have an active journey right now.",
                            "No active journey.", status="done")
        now = now_ist()
        started = journey.start_time
        if started:
            started_aware = started.replace(tzinfo=IST) if started.tzinfo is None else started
            dur_mins = int((now - started_aware).total_seconds() / 60)
            dur_str = f"{dur_mins // 60}h {dur_mins % 60}m" if dur_mins >= 60 else f"{dur_mins}m"
        else:
            dur_str = "Unknown"
        try:
            from app.models.staff_accounts import AssociatedCompany
            comp = db.query(AssociatedCompany).filter(AssociatedCompany.id == journey.company_id).first()
            comp_name = comp.company_name if comp else "N/A"
        except Exception:
            comp_name = "N/A"
        summary = (f"🗺️ End Journey\nCompany: {comp_name}\n"
                   f"Duration so far: {dur_str}\n\nConfirm to stop GPS tracking.")
        return _rb_resp("end_journey", summary, "End the journey?",
                        status="confirming", action_ready=True,
                        resolved={"journey_id": journey.id})
    except Exception as e:
        logger.error(f"[VGK-RB] end_journey error: {e}")
        return _rb_resp("end_journey", "Could not find your active journey. Please use the Journey page.", status="done")


_RB_STOP_WORDS = {
    "search", "find", "show", "me", "for", "a", "an", "the", "do", "you", "have",
    "is", "there", "i", "need", "want", "looking", "available", "availability",
    "price", "cost", "of", "in", "stock", "what", "are", "any", "please", "can",
    "get", "give", "check", "tell", "about", "product", "spare", "part", "item",
}


def _rb_extract_search_query(msg: str) -> str:
    words = re.sub(r"[^\w\s]", " ", msg.lower()).split()
    kept = [w for w in words if w not in _RB_STOP_WORDS and len(w) > 1]
    return " ".join(kept) if kept else msg.strip()


def _rb_marketplace_search(msg: str, msg_lower: str, pairs: List[tuple],
                            db: Session, company_id: int, lang: str = "en") -> Dict:
    # Map Telugu/Hindi spoken words to English search terms first
    mapped_msg = _map_telugu_query(msg)
    query = _rb_extract_search_query(mapped_msg)
    if (not query or len(query) < 2) and pairs:
        mapped_pair = _map_telugu_query(pairs[-1][1])
        query = _rb_extract_search_query(mapped_pair)
    if not query or len(query) < 2:
        what_msg = _L(lang, "what") or "What product or spare part are you looking for?"
        return _rb_resp("marketplace_search", what_msg, what_msg)
    try:
        from app.models.marketplace import MarketspareItem
        items = db.query(MarketspareItem).filter(
            MarketspareItem.company_id == company_id,
            MarketspareItem.is_active == True,
            or_(
                MarketspareItem.name.ilike(f"%{query}%"),
                MarketspareItem.sku.ilike(f"%{query}%"),
                MarketspareItem.category_name.ilike(f"%{query}%"),
                MarketspareItem.model_compat.ilike(f"%{query}%"),
            )
        ).order_by(MarketspareItem.available_qty.desc()).limit(6).all()
        if not items and query.endswith('s') and len(query) > 3:
            singular = query[:-1]
            items = db.query(MarketspareItem).filter(
                MarketspareItem.company_id == company_id,
                MarketspareItem.is_active == True,
                or_(
                    MarketspareItem.name.ilike(f"%{singular}%"),
                    MarketspareItem.sku.ilike(f"%{singular}%"),
                    MarketspareItem.category_name.ilike(f"%{singular}%"),
                    MarketspareItem.model_compat.ilike(f"%{singular}%"),
                )
            ).order_by(MarketspareItem.available_qty.desc()).limit(6).all()
            if items:
                query = singular
        if not items:
            nearby_items = []
            nearby_label = ""
            raw_words = [w for w in re.split(r"\s+", query) if len(w) > 2]
            search_words = []
            for w in raw_words:
                search_words.append(w)
                if w.endswith('s') and len(w) > 3:
                    search_words.append(w[:-1])
                if w.endswith('ies') and len(w) > 4:
                    search_words.append(w[:-3] + 'y')
                if w.endswith('es') and len(w) > 4:
                    search_words.append(w[:-2])
            for word in search_words:
                results = db.query(MarketspareItem).filter(
                    MarketspareItem.company_id == company_id,
                    MarketspareItem.is_active == True,
                    or_(
                        MarketspareItem.name.ilike(f"%{word}%"),
                        MarketspareItem.category_name.ilike(f"%{word}%"),
                    )
                ).order_by(MarketspareItem.available_qty.desc()).limit(6).all()
                if results:
                    nearby_items = results
                    nearby_label = word
                    break
            if not nearby_items:
                nearby_items = db.query(MarketspareItem).filter(
                    MarketspareItem.company_id == company_id,
                    MarketspareItem.is_active == True,
                ).order_by(MarketspareItem.available_qty.desc()).limit(5).all()
                nearby_label = None
            if nearby_items:
                lines = []
                prods = []
                for item in nearby_items:
                    price = f"₹{float(item.dealer_price):.0f}" if item.dealer_price else "—"
                    lines.append(f"• {item.name} [{item.sku}] {price}")
                    prods.append({"id": item.id, "name": item.name, "sku": item.sku,
                                  "price": float(item.dealer_price or 0),
                                  "category_name": item.category_name or "",
                                  "category": item.category_name or "",
                                  "specifications": item.specifications or "",
                                  "model_compat": item.model_compat or "",
                                  "gst_percent": float(item.gst_percent or 18),
                                  "hsn_code": getattr(item, "hsn_code", "") or "",
                                  "image_url": item.image_url or ""})
                if nearby_label:
                    header = (_L(lang, "nearby", query, nearby_label) or
                               f"No exact match for '{query}'. Nearby results for '{nearby_label}':")
                    speak = f"No match for {query}. Showing nearby results for {nearby_label}."
                else:
                    header = (_L(lang, "interested", query) or
                               f"No match for '{query}'. You may also be interested in:")
                    speak = f"No match found. Here are some products from our catalog."
                result = _rb_resp("marketplace_search", f"{header}\n" + "\n".join(lines), speak, status="done")
                result["products"] = prods
                return result
            nf = _L(lang, "not_found", query) or f"No products found for '{query}'. Try a different keyword."
            return _rb_resp("marketplace_search", nf, "No products found.", status="done")
        lines = []
        prods = []
        for item in items:
            price = f"₹{float(item.dealer_price):.0f}" if item.dealer_price else "—"
            spec = f" ({item.specifications})" if item.specifications else ""
            lines.append(f"• {item.name}{spec} [{item.sku}] {price}")
            prods.append({"id": item.id, "name": item.name, "sku": item.sku,
                          "price": float(item.dealer_price or 0),
                          "category_name": item.category_name or "",
                          "category": item.category_name or "",
                          "specifications": item.specifications or "",
                          "model_compat": item.model_compat or "",
                          "gst_percent": float(item.gst_percent or 18),
                          "hsn_code": getattr(item, "hsn_code", "") or "",
                          "image_url": item.image_url or ""})
        found_hdr = _L(lang, "found", query, len(items)) or f"🔍 {len(items)} result(s) for '{query}':\n"
        reply = found_hdr + "\n".join(lines)
        speak = f"Found {len(items)} products for {query}. Top: {items[0].name}."
        result = _rb_resp("marketplace_search", reply, speak, status="done")
        result["products"] = prods
        return result
    except Exception as e:
        logger.error(f"[VGK-RB] marketplace_search error: {e}")
        fail = _L(lang, "failed") or "Catalog search failed. Please use the Marketplace page."
        return _rb_resp("marketplace_search", fail, fail, status="done")


def _rb_general_help(user_name: str, portal_type: str) -> Dict:
    first = (user_name.split()[0] if user_name and user_name.strip() else "there")
    if portal_type == "marketplace":
        reply = (f"Hi {first}! I'm VGK Assistant for VGK4U.\n"
                 "I can help you find EV spare parts.\n\n"
                 "Just tell me what you're looking for:\n"
                 "• Type a product name (e.g. 'Charger', 'Battery')\n"
                 "• Or say 'search mirror' / 'do you have tyre?'\n"
                 "• Check price and stock availability instantly")
        speak = "Tell me what spare part you're looking for."
        opts = []
    elif portal_type == "partner":
        reply = (f"Hi {first}! I'm VGK Assistant. Here's what I can do for you:\n"
                 "• Register a new walk-in customer\n"
                 "• Show today's followups and pending activities\n"
                 "• Create a CRM lead or raise a service ticket\n"
                 "• Search spare parts catalog\n"
                 "• Navigate to any portal page\n\n"
                 "Just type or say what you want to do!")
        speak = "Tell me what you'd like to do."
        opts = [
            {"label": "📝 Register Walk-in", "value": "create walkin"},
            {"label": "📋 Today's Followups", "value": "today's followups"},
            {"label": "🔗 Create CRM Lead", "value": "create lead"},
            {"label": "🔧 Raise Service Ticket", "value": "create service ticket"},
            {"label": "🔍 Search Spare Parts", "value": "search parts"},
        ]
    else:
        reply = (f"Hi {first}! I'm VGK Assistant. I can help you:\n"
                 "• Create tasks, leads, and service tickets\n"
                 "• Start or end your GPS journey\n"
                 "• Check your day plan, tasks, and call stats\n"
                 "• Search the VGK4U spare parts catalog\n\n"
                 "Just type or say what you want to do!")
        speak = "Tell me what you'd like to do."
        opts = []
    result = _rb_resp("general_help", reply, speak, status="done")
    if opts:
        result["options"] = opts
    return result


_CRM_SEGMENT_MAP = {
    "real dreams":      ("Real Dreams",   "/staff/crm/team-leads"),
    "real estate":      ("Real Dreams",   "/staff/crm/team-leads"),
    "property":         ("Real Dreams",   "/staff/crm/team-leads"),
    "ev leads":         ("EV Spares",     "/staff/crm/team-leads"),
    "ev spares leads":  ("EV Spares",     "/staff/crm/team-leads"),
    "ev segment":       ("EV Spares",     "/staff/crm/team-leads"),
    "electric vehicle": ("EV Spares",     "/staff/crm/team-leads"),
    "insurance":        ("Insurance",     "/staff/crm/team-leads"),
    "solar":            ("Solar",         "/staff/crm/team-leads"),
    "etc":              ("ETC Training",  "/staff/crm/team-leads"),
    "training":         ("ETC Training",  "/staff/crm/team-leads"),
    "finance":          ("Finance",       "/staff/crm/team-leads"),
    "general":          ("General",       "/staff/crm/team-leads"),
}


def _rb_query_crm_segment(msg_lower: str, db: Session) -> Dict:
    """DC: Detect which CRM segment the user is asking about and navigate there."""
    segment_name = None
    route = "/staff/crm/team-leads"
    for keyword, (seg, seg_route) in _CRM_SEGMENT_MAP.items():
        if keyword in msg_lower:
            segment_name = seg
            route = seg_route
            break
    if not segment_name:
        segment_name = "All"
    try:
        from app.models.crm import CRMLead
        from app.models.signup_category import SignupCategory
        if segment_name != "All":
            count = db.query(CRMLead).join(
                SignupCategory, CRMLead.category_id == SignupCategory.id, isouter=True
            ).filter(
                SignupCategory.name.ilike(f"%{segment_name}%"),
            ).count()
        else:
            count = db.query(CRMLead).count()
    except Exception:
        count = None
    count_str = f" ({count} leads)" if count is not None else ""
    reply = f"📋 Opening {segment_name} leads{count_str}…\n\nNavigating to Team Leads page."
    speak = f"Opening {segment_name} leads now."
    result = _rb_resp("query_crm_segment", reply, speak, status="done")
    result["route"] = route
    result["segment_name"] = segment_name
    return result


def _rb_query_open_leads(db: Session) -> Dict:
    """DC-ASSISTANT-LEADS-001: Return count of open/pending CRM leads and navigate URL."""
    try:
        from app.models.crm import CRMLead
        count = db.query(CRMLead).filter(CRMLead.status.in_(["new", "open", "pending", "active"])).count()
    except Exception:
        count = None
    count_str = f"{count} open leads" if count is not None else "open leads"
    reply = f"📋 Found {count_str}. Opening CRM with open leads filter…"
    speak = f"Found {count_str}. Opening now."
    result = _rb_resp("query_open_leads", reply, speak, status="done")
    result["route"] = "/staff/crm/team-leads?status=open"
    result["lead_count"] = count
    result["filter_label"] = "Open Leads"
    return result


def _rb_query_today_leads(db: Session) -> Dict:
    """DC-ASSISTANT-LEADS-001: Return count of today's follow-up CRM leads and navigate URL."""
    try:
        from app.models.crm import CRMLead
        today_date = today_ist().date()
        count = db.query(CRMLead).filter(CRMLead.next_followup_date == today_date).count()
    except Exception:
        count = None
    count_str = f"{count} leads due today" if count is not None else "leads due today"
    reply = f"📋 Found {count_str}. Opening CRM with today's follow-up filter…"
    speak = f"Found {count_str}. Opening now."
    result = _rb_resp("query_today_leads", reply, speak, status="done")
    result["route"] = f"/staff/crm/team-leads?date_from={today_ist().date().isoformat()}&date_to={today_ist().date().isoformat()}"
    result["lead_count"] = count
    result["filter_label"] = "Today's Leads"
    return result


def _rb_query_overdue_leads(db: Session) -> Dict:
    """DC-ASSISTANT-LEADS-001: Return count of overdue CRM leads (past follow-up date, not closed)."""
    try:
        from app.models.crm import CRMLead
        from sqlalchemy import and_
        today_date = today_ist().date()
        count = db.query(CRMLead).filter(
            and_(
                CRMLead.next_followup_date < today_date,
                CRMLead.status.notin_(["closed", "converted", "lost"]),
            )
        ).count()
    except Exception:
        count = None
    count_str = f"{count} overdue leads" if count is not None else "overdue leads"
    reply = f"⚠️ Found {count_str} past their follow-up date. Opening CRM…"
    speak = f"Found {count_str} overdue. Opening now."
    result = _rb_resp("query_overdue_leads", reply, speak, status="done")
    result["route"] = f"/staff/crm/team-leads?date_to={today_ist().date().isoformat()}&status=open"
    result["lead_count"] = count
    result["filter_label"] = "Overdue Leads"
    return result


def _rb_query_walkin_leads(db: Session) -> Dict:
    """DC-ASSISTANT-LEADS-001: Return count of walk-in CRM leads and navigate URL."""
    try:
        from app.models.crm import CRMLead
        count = db.query(CRMLead).filter(CRMLead.lead_source.ilike("%walk%")).count()
    except Exception:
        count = None
    count_str = f"{count} walk-in leads" if count is not None else "walk-in leads"
    reply = f"🚶 Found {count_str}. Opening CRM with walk-in filter…"
    speak = f"Found {count_str} walk-in leads. Opening now."
    result = _rb_resp("query_walkin_leads", reply, speak, status="done")
    result["route"] = "/staff/crm/team-leads?lead_type=walkin"
    result["lead_count"] = count
    result["filter_label"] = "Walk-in Leads"
    return result


def _query_partner_activity(partner_id: int, db: Session, language: str = "en") -> Dict:
    """DC: Return today's followup leads and walkins for a partner."""
    from sqlalchemy import text as sq_text
    today = today_ist().date()
    lines: List[str] = []

    # ── CRM leads due today ────────────────────────────────────────────────────
    try:
        rows = db.execute(sq_text("""
            SELECT cl.lead_name, cl.phone, cl.status,
                   sc.name AS category, cl.next_followup_date
            FROM crm_leads cl
            LEFT JOIN signup_categories sc ON sc.id = cl.category_id
            WHERE cl.associated_partner_id = :pid
              AND cl.next_followup_date = :today
              AND cl.status NOT IN ('closed','converted','lost')
            ORDER BY cl.next_followup_date, cl.lead_name
            LIMIT 15
        """), {"pid": partner_id, "today": today}).fetchall()
        if rows:
            lines.append("📞 *CRM Leads — Follow Up Today:*")
            for r in rows:
                cat = r[3] or "General"
                lines.append(f"  • {r[0]} | {r[1]} | {cat} | {r[2]}")
    except Exception as e:
        logger.warning(f"[VGK] partner activity CRM query error: {e}")

    # ── Walkins needing followup today ─────────────────────────────────────────
    try:
        rows2 = db.execute(sq_text("""
            SELECT customer_name, customer_phone, visit_purpose, visit_outcome
            FROM partner_walkins
            WHERE partner_id = :pid
              AND follow_up_date = :today
              AND visit_outcome NOT IN ('converted','closed')
            ORDER BY customer_name
            LIMIT 10
        """), {"pid": partner_id, "today": today}).fetchall()
        if rows2:
            lines.append("\n🚶 *Walk-in Followups Due Today:*")
            for r in rows2:
                lines.append(f"  • {r[0]} | {r[1]} | {r[2]} | outcome: {r[3]}")
    except Exception as e:
        logger.warning(f"[VGK] partner activity walkin query error: {e}")

    if not lines:
        msgs = {
            "en": "✅ No followups scheduled for today. You're all clear!",
            "hi": "✅ आज के लिए कोई फॉलो-अप निर्धारित नहीं है।",
            "te": "✅ నేడు ఫాలో-అప్‌లు నిర్ణయించబడలేదు.",
        }
        reply = msgs.get(language, msgs["en"])
    else:
        hdr = {
            "en": f"📋 Today's Activity ({today.strftime('%d %b %Y')}):\n",
            "hi": f"📋 आज की गतिविधि ({today.strftime('%d %b %Y')}):\n",
            "te": f"📋 నేటి కార్యకలాపం ({today.strftime('%d %b %Y')}):\n",
        }
        reply = hdr.get(language, hdr["en"]) + "\n".join(lines)

    speak = {
        "en": f"You have {len(lines)} followup items today.",
        "hi": f"आज {len(lines)} फॉलो-अप हैं।",
        "te": f"నేడు {len(lines)} ఫాలో-అప్‌లు ఉన్నాయి.",
    }.get(language, f"You have {len(lines)} followup items today.")

    return _rb_resp("query_partner_activity", reply, speak, status="done")


def _rb_create_walkin(msg: str, pairs: List[tuple]) -> Dict:
    """Rule-based walkin data collection flow."""
    cname = cphone = purpose = None
    for q, a in pairs:
        if any(k in q for k in ("customer name", "customer's name", "name", "naam")):
            cname = a.strip()
        elif any(k in q for k in ("phone", "mobile", "number", "contact")):
            cphone = re.sub(r"[^\d+]", "", a)
        elif any(k in q for k in ("purpose", "visit purpose", "reason", "interest", "category")):
            purpose = a.strip().lower()

    if not cname:
        return _rb_resp("create_walkin", "What is the customer's name?", "Customer name?")
    if not cphone:
        return _rb_resp("create_walkin", f"Got it — {cname}. What is their phone number?", "Phone number?",
                        resolved={"customer_name": cname})
    if not purpose:
        opts = [
            {"label": "General Enquiry", "value": "general"},
            {"label": "EV / Electric Vehicle", "value": "ev"},
            {"label": "Real Estate", "value": "real_estate"},
            {"label": "Insurance", "value": "insurance"},
            {"label": "Solar", "value": "solar"},
        ]
        return _rb_resp("create_walkin",
                        f"What is the visit purpose for {cname}?",
                        "Visit purpose?",
                        options=opts,
                        resolved={"customer_name": cname, "customer_phone": cphone})

    purpose_map = {"ev": "ev", "electric": "ev", "real estate": "real_estate", "real_estate": "real_estate",
                   "insurance": "insurance", "solar": "solar", "general": "general"}
    visit_purpose = next((v for k, v in purpose_map.items() if k in purpose), "general")
    summary = (f"✅ Walkin ready to record:\n"
               f"  Customer: {cname}\n  Phone: {cphone}\n  Purpose: {visit_purpose}\n\nConfirm?")
    return _rb_resp("create_walkin", summary, f"Walkin for {cname} — confirm?",
                    status="confirming", action_ready=True,
                    resolved={"customer_name": cname, "customer_phone": cphone,
                              "visit_purpose": visit_purpose})


def _rule_based_fallback(req: VGKRequest, portal_type: str, user_name: str,
                          emp_code: str, employee_id: Optional[int], db: Session,
                          partner_id: Optional[int] = None) -> Dict:
    """Rule-based NLP engine. Active when Gemini API is unavailable."""
    msg = req.user_message.strip()
    msg_lower = msg.lower()
    intent = _rb_detect_intent(msg_lower, req.conversation_history, portal_type)
    pairs = _rb_pairs(req.conversation_history, msg)

    if intent == "query_day_planner" and employee_id:
        r = _query_day_planner(employee_id, db, req.language)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_tasks" and employee_id:
        r = _query_tasks(employee_id, db, req.language)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_talk_time" and employee_id:
        r = _query_talk_time(employee_id, db, req.language)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "end_journey":
        return _rb_end_journey(employee_id, db)
    if intent == "marketplace_search":
        return _rb_marketplace_search(msg, msg_lower, pairs, db, req.company_id or 1, getattr(req, "language", "en") or "en")
    if intent == "query_crm_segment":
        return _rb_query_crm_segment(msg_lower, db)
    if intent == "query_open_leads":
        return _rb_query_open_leads(db)
    if intent == "query_today_leads":
        return _rb_query_today_leads(db)
    if intent == "query_overdue_leads":
        return _rb_query_overdue_leads(db)
    if intent == "query_walkin_leads":
        return _rb_query_walkin_leads(db)
    if intent == "start_journey":
        return _rb_start_journey(pairs, db)
    if intent == "create_task":
        return _rb_create_task(msg, pairs, employee_id, db)
    if intent == "create_lead":
        return _rb_create_lead(msg, pairs)
    if intent == "create_service_ticket":
        return _rb_create_ticket(msg, pairs)
    if intent == "create_walkin":
        return _rb_create_walkin(msg, pairs)
    if intent == "query_partner_activity":
        if partner_id:
            return _query_partner_activity(partner_id, db, req.language)
        return _rb_resp("query_partner_activity",
                        "⚠️ Could not identify your partner account. Please log in again.",
                        "Partner account not found.", status="done")
    if intent == "query_attendance" and employee_id:
        try:
            from app.models.staff_attendance import StaffAttendance
            today_date = today_ist().date()
            att = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == employee_id,
                StaffAttendance.date == today_date
            ).first()
            if att:
                worked_h = round((att.worked_minutes or 0) / 60, 1)
                ci = att.clock_in.strftime('%I:%M %p') if att.clock_in else 'Not clocked in'
                co = att.clock_out.strftime('%I:%M %p') if att.clock_out else 'Not clocked out'
                gps = (att.gps_status or 'unknown').replace('_', ' ').title()
                reply = f"✅ Today's attendance: Clocked in at {ci}, out: {co}. Worked: {worked_h}h. GPS: {gps}."
            else:
                reply = "⚠️ No attendance record for today. Please clock in from the attendance page."
            return _rb_resp("query_attendance", reply, reply[:60], status="done")
        except Exception as _ae:
            logger.warning(f"[VGK] rb query_attendance error: {_ae}")
    if intent == "edit_task":
        return _rb_resp("navigate", "To edit a task, please go to your Tasks page.",
                        "Opening tasks page.", status="done",
                        resolved={"route": "/staff/task-tracker"}, action_ready=True)
    if intent == "log_call":
        return _rb_resp("navigate", "Opening Call Management to log your call.",
                        "Opening call management.", status="done",
                        resolved={"route": "/staff/call-management"}, action_ready=True)
    return _rb_general_help(user_name, portal_type)


async def _process(req: VGKRequest, portal_type: str, user_name: str,
                   emp_code: str, employee_id: Optional[int], db: Session,
                   partner_id: Optional[int] = None) -> VGKResponse:
    today_str = today_ist().isoformat()
    system_prompt = _build_system_prompt(
        portal_type, user_name, emp_code, today_str, req.language,
        allowed_intents=req.allowed_intents,
        accessible_routes=getattr(req, 'accessible_routes', None)
    )

    history = [{"role": t.role, "text": t.text} for t in req.conversation_history]
    history.append({"role": "user", "text": req.user_message})

    try:
        gemini_resp = await _call_gemini(system_prompt, history)
    except Exception as e:
        logger.warning(f"[VGK] Gemini unavailable, using rule-based fallback: {e}")
        rb = _rule_based_fallback(req, portal_type, user_name, emp_code, employee_id, db,
                                  partner_id=partner_id)
        return VGKResponse(
            success=True,
            intent=rb["intent"],
            reply_text=rb["reply_text"],
            speak_text=rb["speak_text"],
            status=rb["status"],
            options=rb["options"],
            action_ready=rb["action_ready"],
            action_type=rb["intent"] if rb["action_ready"] else None,
            resolved_data=rb["resolved_data"],
            employee_matches=rb["employee_matches"],
        )

    intent = gemini_resp.get("intent", "unknown")

    # DC: Gate — if Gemini returns an intent not allowed for this portal, redirect to general_help
    portal_allowed = _PORTAL_ALLOWED_INTENTS.get(portal_type, set())
    if portal_allowed and intent not in portal_allowed and intent not in ("clarify", "unknown"):
        logger.warning(f"[VGK] Gemini returned out-of-scope intent '{intent}' for portal '{portal_type}' — overriding to general_help")
        intent = "general_help"
        gemini_resp["intent"] = "general_help"
    reply_text = gemini_resp.get("reply_text", "")
    speak_text = gemini_resp.get("speak_text", reply_text)
    status = gemini_resp.get("status", "collecting")
    options = gemini_resp.get("options", [])
    action_ready = gemini_resp.get("action_ready", False)
    resolved_data = gemini_resp.get("resolved_data", {})
    fuzzy_lookup = gemini_resp.get("fuzzy_lookup")
    employee_matches = []

    if fuzzy_lookup and fuzzy_lookup.get("query") and employee_id is not None:
        matches = _fuzzy_employees(fuzzy_lookup["query"], db)
        if len(matches) == 1:
            resolved_data[fuzzy_lookup["field"]] = matches[0]["name"]
            resolved_data["primary_assignee_id"] = int(matches[0]["value"])
            reply_msgs = {
                "en": f"Got it — assigning to {matches[0]['name']}. ",
                "hi": f"ठीक है — {matches[0]['name']} को असाइन कर रहे हैं। ",
                "te": f"సరే — {matches[0]['name']} కి అసైన్ చేస్తున్నాం. "
            }
            reply_text = reply_msgs.get(req.language, reply_msgs["en"]) + reply_text
        elif len(matches) > 1:
            employee_matches = matches
            options = [{"label": m["label"], "value": m["value"]} for m in matches]
            choose_msgs = {
                "en": f"I found {len(matches)} people named '{fuzzy_lookup['query']}'. Which one?",
                "hi": f"'{fuzzy_lookup['query']}' नाम के {len(matches)} लोग मिले। कौन सा?",
                "te": f"'{fuzzy_lookup['query']}' పేరుతో {len(matches)} వ్యక్తులు కనుగొనబడ్డారు. ఏది?"
            }
            reply_text = choose_msgs.get(req.language, choose_msgs["en"])
            speak_text = reply_text
            status = "collecting"
            action_ready = False
        else:
            no_match_msgs = {
                "en": f"No staff member found for '{fuzzy_lookup['query']}'. Please try a different name.",
                "hi": f"'{fuzzy_lookup['query']}' नाम का कोई स्टाफ नहीं मिला। कृपया दोबारा कोशिश करें।",
                "te": f"'{fuzzy_lookup['query']}' పేరుతో స్టాఫ్ కనుగొనబడలేదు. దయచేసి మరో పేరు ప్రయత్నించండి."
            }
            reply_text = no_match_msgs.get(req.language, no_match_msgs["en"])
            speak_text = reply_text
            status = "collecting"
            action_ready = False

    if employee_id is not None and intent == "query_day_planner" and status in ("done", "confirming"):
        result = _query_day_planner(employee_id, db, req.language)
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if employee_id is not None and intent == "query_tasks" and status in ("done", "confirming"):
        result = _query_tasks(employee_id, db, req.language)
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if employee_id is not None and intent == "query_talk_time" and status in ("done", "confirming"):
        result = _query_talk_time(employee_id, db, req.language)
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if intent == "start_journey" and status == "collecting" and not resolved_data.get("company_name"):
        try:
            from app.models.sfms import AssociatedCompany
            companies = db.query(AssociatedCompany).filter(
                AssociatedCompany.is_active == True
            ).order_by(AssociatedCompany.company_name).limit(10).all()
            if companies:
                options = [{"label": c.company_name, "value": str(c.id)} for c in companies]
        except Exception:
            pass

    if intent == "end_journey" and status in ("done", "confirming", "collecting"):
        rb = _rb_end_journey(employee_id, db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        status = rb["status"]
        action_ready = rb["action_ready"]
        if rb["resolved_data"]:
            resolved_data.update(rb["resolved_data"])

    marketplace_products: List[Dict] = []
    if intent == "marketplace_search" and status in ("done", "confirming", "collecting"):
        query = resolved_data.get("search_query", "") or req.user_message
        rb = _rb_marketplace_search(
            req.user_message, req.user_message.lower(),
            [], db, req.company_id or 1,
            getattr(req, 'language', 'en') or 'en'
        )
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        status = "done"
        action_ready = False
        marketplace_products = rb.get("products", [])

    if intent == "query_crm_segment" and status in ("done", "confirming", "collecting"):
        segment_name = resolved_data.get("segment_name") or req.user_message
        rb = _rb_query_crm_segment(segment_name.lower(), db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        resolved_data["route"] = rb.get("route", "/staff/crm/team-leads")
        resolved_data["segment_name"] = rb.get("segment_name", "")
        status = "done"
        action_ready = True

    if intent == "query_open_leads":
        rb = _rb_query_open_leads(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        resolved_data["route"] = rb.get("route", "/staff/crm/team-leads?status=open")
        resolved_data["lead_count"] = rb.get("lead_count")
        resolved_data["filter_label"] = rb.get("filter_label", "Open Leads")
        status = "done"
        action_ready = True

    if intent == "query_today_leads":
        rb = _rb_query_today_leads(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        resolved_data["route"] = rb.get("route", "/staff/crm/team-leads")
        resolved_data["lead_count"] = rb.get("lead_count")
        resolved_data["filter_label"] = rb.get("filter_label", "Today's Leads")
        status = "done"
        action_ready = True

    if intent == "query_overdue_leads":
        rb = _rb_query_overdue_leads(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        resolved_data["route"] = rb.get("route", "/staff/crm/team-leads")
        resolved_data["lead_count"] = rb.get("lead_count")
        resolved_data["filter_label"] = rb.get("filter_label", "Overdue Leads")
        status = "done"
        action_ready = True

    if intent == "query_walkin_leads":
        rb = _rb_query_walkin_leads(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        resolved_data["route"] = rb.get("route", "/staff/crm/team-leads?lead_type=walkin")
        resolved_data["lead_count"] = rb.get("lead_count")
        resolved_data["filter_label"] = rb.get("filter_label", "Walk-in Leads")
        status = "done"
        action_ready = True

    if employee_id is not None and intent == "query_attendance":
        try:
            from app.models.staff_attendance import StaffAttendance
            today_date = today_ist().date()
            att = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == employee_id,
                StaffAttendance.date == today_date
            ).first()
            if att:
                worked_h = round((att.worked_minutes or 0) / 60, 1)
                ci = att.clock_in.strftime('%I:%M %p') if att.clock_in else 'Not clocked in'
                co = att.clock_out.strftime('%I:%M %p') if att.clock_out else 'Not clocked out'
                gps = (att.gps_status or 'unknown').replace('_', ' ').title()
                msgs = {
                    "en": f"✅ Today's attendance: Clocked in at {ci}, Clocked out: {co}. Worked: {worked_h}h. GPS: {gps}.",
                    "hi": f"✅ आज की उपस्थिति: {ci} पर क्लॉक-इन, क्लॉक-आउट: {co}. काम किया: {worked_h}h. GPS: {gps}.",
                    "te": f"✅ నేటి హాజరు: {ci}కి క్లాక్-ఇన్, క్లాక్-అవుట్: {co}. పని సమయం: {worked_h}h. GPS: {gps}.",
                }
                reply_text = msgs.get(req.language, msgs["en"])
                speak_text = reply_text[:80]
            else:
                no_att = {
                    "en": "⚠️ No attendance record for today. Please clock in from the attendance page.",
                    "hi": "⚠️ आज का कोई उपस्थिति रिकॉर्ड नहीं मिला। कृपया अटेंडेंस पेज से क्लॉक-इन करें।",
                    "te": "⚠️ ఈ రోజు హాజరు రికార్డు లేదు. దయచేసి హాజరు పేజీ నుండి క్లాక్-ఇన్ చేయండి.",
                }
                reply_text = no_att.get(req.language, no_att["en"])
                speak_text = reply_text
            status = "done"
            action_ready = False
        except Exception as _ae:
            logger.warning(f"[VGK] query_attendance error: {_ae}")

    if intent == "navigate" and resolved_data.get("route"):
        action_ready = True
        status = "done"

    if intent == "log_call" and action_ready:
        status = "done"

    if intent == "query_kra" and status in ("done", "confirming"):
        action_ready = True
        status = "done"
        resolved_data.setdefault("route", "/staff/kra")

    if intent == "query_partner_activity" and partner_id:
        r = _query_partner_activity(partner_id, db, req.language)
        reply_text = r["reply_text"]
        speak_text = r["speak_text"]
        status = "done"
        action_ready = False

    # create_walkin: backend only collects fields + confirms — actual INSERT is done by frontend via POST /partner/walkins
    if intent == "create_walkin" and action_ready:
        status = "confirming"

    return VGKResponse(
        success=True,
        intent=intent,
        reply_text=reply_text,
        speak_text=speak_text,
        status=status,
        options=options,
        action_ready=action_ready,
        action_type=intent if action_ready else None,
        resolved_data=resolved_data,
        employee_matches=employee_matches,
        products=marketplace_products
    )


# ─── Staff Endpoint ────────────────────────────────────────────────────────────

@router.post("/staff/process", response_model=VGKResponse, summary="VGK Assistant — Staff Portal")
async def vgk_staff_process(
    req: VGKRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffEmployee = Depends(get_current_staff_user)
):
    return await _process(
        req=req,
        portal_type="staff",
        user_name=current_user.full_name or current_user.emp_code or "Staff",
        emp_code=current_user.emp_code,
        employee_id=current_user.id,
        db=db
    )


# ─── Partner Endpoint ──────────────────────────────────────────────────────────

@router.post("/partner/process", response_model=VGKResponse, summary="VGK Assistant — Partner Portal")
async def vgk_partner_process(
    req: VGKRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_partner: OfficialPartner = Depends(get_current_partner)
):
    return await _process(
        req=req,
        portal_type="partner",
        user_name=current_partner.partner_name or current_partner.partner_code,
        emp_code=current_partner.partner_code,
        employee_id=None,
        db=db,
        partner_id=current_partner.id,
    )


# ─── Public / Marketplace Endpoint ─────────────────────────────────────────────

@router.post("/public/process", response_model=VGKResponse, summary="VGK Assistant — Public / Marketplace")
async def vgk_public_process(
    req: VGKRequest,
    db: Session = Depends(get_db)
):
    """
    No-auth endpoint for the public marketplace page.
    Scoped to marketplace_search and general_help only.
    Rule-based only (no Gemini) — keeps latency low for public users.
    """
    msg = req.user_message.strip()
    msg_lower = msg.lower()
    pairs = _rb_pairs(req.conversation_history, msg)

    intent = _rb_detect_intent(msg_lower, req.conversation_history, portal_type="marketplace")

    if intent not in ("marketplace_search", "general_help"):
        intent = "marketplace_search"

    if intent == "marketplace_search":
        result = _rb_marketplace_search(msg, msg_lower, pairs, db, req.company_id or 1, getattr(req, "language", "en") or "en")
        return VGKResponse(
            success=True,
            intent="marketplace_search",
            reply_text=result["reply_text"],
            speak_text=result["speak_text"],
            status=result["status"],
            options=[],
            action_ready=False,
            action_type=None,
            resolved_data={},
            employee_matches=[],
            products=result.get("products", [])
        )

    result = _rb_general_help("", "marketplace")
    return VGKResponse(
        success=True,
        intent="general_help",
        reply_text=result["reply_text"],
        speak_text=result["speak_text"],
        status="done",
        options=[],
        action_ready=False,
        action_type=None,
        resolved_data={},
        employee_matches=[]
    )
