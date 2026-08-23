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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
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
    "query_journeys":        [],
    "query_whatsapp":        [],
    "send_whatsapp_report":  [],
    "query_time":            [],
    "query_kra":             ["staff_kra", "staff_my_kra", "staff_kra_dashboard"],
    "log_call":              ["call_tracking_dashboard", "staff_my_leads", "staff_crm_dashboard"],
    "query_cash_statement":  ["expense_dashboard"],
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
        "query_journeys":        "- query_journeys        : Check active or today's field journeys logged by staff",
        "query_whatsapp":        "- query_whatsapp        : Check recent WhatsApp bot message delivery history and logs",
        "send_whatsapp_report":  "- send_whatsapp_report  : Share or send daily reports to WhatsApp sales groups using bot",
        "query_time":            "- query_time            : Check current system date, time, and clock in IST",
        "edit_task":              "- edit_task              : Edit an existing task. Required: task_code or partial title, field_to_edit, new_value",
        "navigate":              "- navigate               : Open/go to any page or module. E.g., 'go to CRM', 'open service queue', 'show my journeys'. Set resolved_data.route to the matching path.",
        "query_attendance":      "- query_attendance       : Check today's attendance status, check-in time, worked hours, GPS status.",
        "query_kra":             "- query_kra              : Check KRA (Key Result Area) performance targets and current status.",
        "log_call":              "- log_call               : Log a call quickly. Required: contact_name, phone, duration_minutes, outcome (connected/not_answered/callback_requested)",
        "create_walkin":         "- create_walkin          : Record a new customer walk-in visit at your showroom. Required: customer_name, phone, visit_purpose (general/ev/real_estate/insurance/solar)",
        "query_partner_activity": "- query_partner_activity : Show today's followups and pending activities — CRM leads due today, walkins needing followup.",
        "query_cash_statement":  "- query_cash_statement  : Show financial cash statement, total cash in and cash out, bank in and bank out, category breakups, and today's/weekly summary.",
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
    api_key = (os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    gemini_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{gemini_model}:generateContent?key={api_key}"
    )

    contents = []
    for turn in conversation:
        role = "user" if turn.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": turn.get("text", "")}]})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 512,
            "responseMimeType": "application/json"
        }
    }

    try:
        import httpx as _httpx
    except ImportError:
        raise HTTPException(status_code=503, detail="VGK Assistant AI service is not available on this server.")
    async with _httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(gemini_url, json=payload)
        if resp.status_code != 200:
            err_text = resp.text[:500]
            logger.error(f"[VGK] Gemini {resp.status_code} from {gemini_model}: {err_text}")
            if resp.status_code == 400 and "API_KEY_INVALID" in err_text:
                raise HTTPException(status_code=503, detail="VGK Assistant API key invalid. Contact your administrator.")
            if resp.status_code in (403, 429) and ("SERVICE_DISABLED" in err_text or "PERMISSION_DENIED" in err_text):
                raise HTTPException(status_code=503, detail="VGK Assistant AI service permission error. Please update your API key in backend/.env.")
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


def _query_attendance(employee_id: Optional[int], db: Session, language: str = "en", msg_lower: str = "") -> Dict:
    """
    DC_ATTENDANCE_QUERY_001 — Unified Staff & Team Attendance Engine.
    Handles both individual and team-wide attendance queries.
    """
    try:
        from app.models.staff_attendance import StaffAttendance
        from app.models.staff import StaffEmployee
        today_date = today_ist()

        is_team_query = any(w in msg_lower for w in ["who", "all", "team", "staff", "present", "absent", "everyone", "logged", "online", "any", "active", "in office"]) or not employee_id

        if is_team_query:
            att_rows = db.query(StaffAttendance, StaffEmployee).join(
                StaffEmployee, StaffEmployee.id == StaffAttendance.employee_id
            ).filter(
                StaffAttendance.date == today_date,
                StaffEmployee.status == "active"
            ).all()

            if att_rows:
                present_list = []
                half_day_list = []
                absent_list = []

                for att, emp in att_rows:
                    ci = att.clock_in.strftime('%I:%M %p') if att.clock_in else 'Not clocked in'
                    co = att.clock_out.strftime('%I:%M %p') if att.clock_out else 'Active'
                    st = (att.status or "").lower()

                    if st in ("present", "clocked_in", "completed"):
                        present_list.append(f"• **{emp.full_name}** (`{emp.emp_code}`) — In: {ci} | Out: {co}")
                    elif st in ("half_day", "partial"):
                        half_day_list.append(f"• **{emp.full_name}** (`{emp.emp_code}`) — In: {ci}")
                    else:
                        absent_list.append(f"• **{emp.full_name}** (`{emp.emp_code}`)")

                lines = [f"📋 **Today's Team Attendance Report ({today_date.strftime('%d %b %Y')}):**\n"]
                if present_list:
                    lines.append(f"🟢 **Present / Clocked In ({len(present_list)} Staff):**")
                    lines.extend(present_list)
                    lines.append("")
                if half_day_list:
                    lines.append(f"🌗 **Half Day ({len(half_day_list)} Staff):**")
                    lines.extend(half_day_list)
                    lines.append("")
                if absent_list:
                    lines.append(f"🔴 **Absent / Not Clocked In ({len(absent_list)} Staff):**")
                    lines.extend(absent_list)

                reply = "\n".join(lines)
                speak = f"Found {len(present_list)} staff present today."
                return {"reply_text": reply, "speak_text": speak}
            else:
                return {
                    "reply_text": f"📋 No attendance records logged yet for today ({today_date.strftime('%d %b %Y')}).",
                    "speak_text": "No attendance records logged for today."
                }
        else:
            att = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == employee_id,
                StaffAttendance.date == today_date
            ).first()
            if att:
                worked_h = round((att.worked_minutes or 0) / 60, 1)
                ci = att.clock_in.strftime('%I:%M %p') if att.clock_in else 'Not clocked in'
                co = att.clock_out.strftime('%I:%M %p') if att.clock_out else 'Not clocked out'
                gps = (att.gps_status or 'unknown').replace('_', ' ').title()
                reply = f"✅ **Today's Attendance Status:** Clocked in at {ci}, out: {co}. Worked: {worked_h}h. GPS: {gps}."
            else:
                reply = "⚠️ No attendance record for today. Please clock in from the attendance page."
            return {"reply_text": reply, "speak_text": reply}

    except Exception as exc:
        logger.warning(f"[VGK] query_attendance error: {exc}")
        return {"reply_text": "Error retrieving attendance status.", "speak_text": "Error retrieving attendance status."}


def _query_tasks(employee_id: Optional[int], db: Session, language: str = "en", msg_lower: str = "") -> Dict:
    """
    DC_TASKS_QUERY_001 — Unified Staff & Team Task Engine.
    """
    try:
        from app.models.staff_tasks import StaffTask
        from app.models.staff import StaffEmployee
        from sqlalchemy import desc

        is_team_query = any(w in msg_lower for w in ["all", "team", "pending", "open", "show"]) or not employee_id

        if is_team_query or (employee_id in (1, 28, 34, 47)):
            tasks_query = db.query(StaffTask, StaffEmployee).outerjoin(
                StaffEmployee, StaffEmployee.id == StaffTask.primary_assignee_id
            ).filter(
                StaffTask.status.in_(["pending", "in_progress", "on_hold"])
            ).order_by(
                desc(StaffTask.priority == "critical"),
                desc(StaffTask.priority == "high"),
                StaffTask.due_date
            ).limit(10).all()

            if tasks_query:
                lines = [f"📋 **Active Team Tasks ({len(tasks_query)} items):**\n"]
                for idx, (t, emp) in enumerate(tasks_query, 1):
                    assignee_str = f" → assigned to *{emp.full_name}*" if emp else ""
                    due_str = f" (due {t.due_date.strftime('%d %b')})" if t.due_date else ""
                    lines.append(f"{idx}. **[{t.priority.upper()}]** {t.title}{assignee_str}{due_str} — Status: *{(t.status or 'pending').title()}*")
                reply = "\n".join(lines)
                speak = f"Found {len(tasks_query)} active team tasks."
                return {"reply_text": reply, "speak_text": speak}

        if employee_id:
            tasks = db.query(StaffTask).filter(
                StaffTask.primary_assignee_id == employee_id,
                StaffTask.status.in_(["pending", "in_progress", "on_hold"])
            ).order_by(
                desc(StaffTask.priority == "critical"),
                desc(StaffTask.priority == "high"),
                StaffTask.due_date
            ).limit(5).all()

            if tasks:
                lines = [f"📋 **Your Active Tasks ({len(tasks)} items):**\n"]
                for idx, t in enumerate(tasks, 1):
                    due_str = f" (due {t.due_date.strftime('%d %b')})" if t.due_date else ""
                    lines.append(f"{idx}. **[{t.priority.upper()}]** {t.title}{due_str}")
                reply = "\n".join(lines)
                speak = f"You have {len(tasks)} active tasks."
                return {"reply_text": reply, "speak_text": speak}

        return {"reply_text": "Great news — no pending tasks right now!", "speak_text": "No pending tasks right now."}
    except Exception as exc:
        logger.warning(f"[VGK] query_tasks error: {exc}")
        return {"reply_text": "Error retrieving tasks.", "speak_text": "Error retrieving tasks."}


def _query_talk_time(employee_id: Optional[int], db: Session, language: str = "en", msg_lower: str = "") -> Dict:
    """
    DC_TALK_TIME_002 — Comprehensive Staff & Team Call Performance Engine.
    Queries unified sales performance stats (Mobile + MyOperator Cloud Calls).
    Supports Today, Yesterday, This Week, and This Month queries.
    """
    try:
        from app.services.sales_performance_report_service import get_today_sales_performance_stats
        
        ist_now = today_ist()
        start_date = ist_now
        end_date = ist_now
        period_label = "Today"

        if any(w in msg_lower for w in ["week", "weekly", "7 days", "overall week", "past week", "this week"]):
            start_date = ist_now - timedelta(days=6)
            end_date = ist_now
            period_label = "This Week (Past 7 Days)"
        elif any(w in msg_lower for w in ["yesterday", "last day", "previous day"]):
            start_date = ist_now - timedelta(days=1)
            end_date = start_date
            period_label = "Yesterday"
        elif any(w in msg_lower for w in ["month", "monthly", "this month"]):
            start_date = ist_now.replace(day=1)
            end_date = ist_now
            period_label = "This Month"

        stats = get_today_sales_performance_stats(db, start_date=start_date, end_date=end_date, period_label=period_label)
        
        lb = stats.get("leaderboard", [])
        active_lb = [item for item in lb if item.get("call_count", 0) > 0 or item.get("talk_seconds", 0) > 0]
        
        if active_lb:
            highest_talk = max(active_lb, key=lambda x: x.get("talk_seconds", 0))
            highest_calls = max(active_lb, key=lambda x: x.get("call_count", 0))
            
            lines = [
                f"📞 **{period_label}'s Team Telecalling & Talk Time Report ({stats.get('date_str', '')}):**\n",
                f"• **Total Calls Handled**: {stats.get('total_calls', 0)} calls",
                f"• **Total Team Talk Time**: {stats.get('total_talk_formatted', '0m')}",
                f"• **Missed Calls**: {stats.get('missed_calls', 0)} calls\n",
                f"🏆 **Highest Talk Time ({period_label})**: **{highest_talk['handled_by']}** with **{highest_talk['talk_time_formatted']}** ({highest_talk['call_count']} calls)\n",
                f"🥇 **Highest Call Volume ({period_label})**: **{highest_calls['handled_by']}** with **{highest_calls['call_count']} calls** ({highest_calls['talk_time_formatted']})\n",
                "📋 **Staff Performance Breakdown:**"
            ]
            
            for idx, item in enumerate(active_lb, 1):
                missed_str = f" (🔴 {item['missed_count']} Missed)" if item.get("missed_count", 0) > 0 else ""
                lines.append(f"{idx}. **{item['handled_by']}** — {item['talk_time_formatted']} Talk Time | {item['call_count']} Calls{missed_str}")
            
            idle_lb = [item for item in lb if item.get("call_count", 0) == 0]
            if idle_lb:
                lines.append(f"\n📋 **Zero Calls ({period_label}):**")
                for item in idle_lb:
                    lines.append(f"• **{item['handled_by']}** — 0 Calls | 0m Talk Time")
            
            reply_text = "\n".join(lines)
            speak_text = f"Highest talk time for {period_label} is {highest_talk['handled_by']} with {highest_talk['talk_time_formatted']}."
            return {"reply_text": reply_text, "speak_text": speak_text}
            
    except Exception as exc:
        logger.warning(f"Failed to fetch team talk time stats: {exc}")
        
    if employee_id:
        today_str = today_ist().strftime("%Y-%m-%d")
        logs = db.query(CallLog).filter(
            CallLog.staff_id == employee_id,
            CallLog.call_date == today_str
        ).all()

        if logs:
            total = len(logs)
            total_sec = sum(l.duration_seconds or 0 for l in logs)
            outgoing = sum(1 for l in logs if (l.call_type or "").lower() in ("outgoing", "out"))
            incoming = sum(1 for l in logs if (l.call_type or "").lower() in ("incoming", "in"))
            missed = total - outgoing - incoming
            txt = f"Today: {total} calls, talk time {format_duration(total_sec)} — {outgoing} outgoing, {incoming} incoming, {missed} missed."
            return {"reply_text": txt, "speak_text": txt}

    return {"reply_text": "No calls recorded today yet.", "speak_text": "No calls recorded today yet."}


# ═══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK ENGINE — DC Protocol
# Active when Gemini API is unavailable. Handles all intents via keyword + state.
# ═══════════════════════════════════════════════════════════════════════════════

_RB_KEYWORDS: Dict[str, List[str]] = {
    "query_today_leads":     [
        "what all new leads added today", "what new leads added today", "new leads added today",
        "leads added today", "leads created today", "leads came today", "leads added", "what new leads",
        "today leads", "today's leads", "today followup leads", "leads today",
        "follow up today leads", "today crm", "due today", "leads due today",
        "show today leads", "today's followup", "scheduled today",
    ],
    "query_open_leads":      [
        "open leads", "new leads", "pending leads", "show open leads", "open crm",
        "unassigned leads", "fresh leads", "status open", "leads not closed",
        "show new leads", "view open leads", "my open leads", "active leads",
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
    "query_attendance":      [
        "who are present today", "who is present today", "who is present", "who are present",
        "who is absent today", "who is absent", "who are absent", "attendance today", "staff attendance",
        "today attendance", "present staff", "absent staff", "who clocked in", "who is in office",
        "who is working today", "attendance report", "my attendance", "am i clocked in", "clock in status",
        "present today", "absent today", "today present", "logged in", "still logged in", "logged in staff",
        "anyone logged in", "anyone still logged in", "any one logged in", "any one still logged in",
        "is anyone logged in", "is anyone still logged in", "is there anyone logged in", "is there anyone still logged in",
        "is there any one logged in", "is there any one still logged in", "who is logged in", "who is online",
        "logged in users", "active staff", "clocked in staff", "who is active"
    ],
    "query_tasks":           [
        "pending tasks", "show pending tasks", "all pending tasks", "open tasks",
        "show open tasks", "my tasks", "pending task", "show tasks", "task list",
        "open task", "active tasks", "list tasks", "show my tasks", "what tasks",
        "tasks assigned", "team tasks"
    ],
    "query_talk_time":       [
        "highest talk time", "who has done highest talk time", "who has dont highest talk time",
        "highest talk", "who talked most", "most talk time", "who has highest talk time",
        "highest calls", "who made most calls", "who has most calls", "most calls today",
        "call leaderboard", "staff wise talk time", "staff talk time", "top telecaller",
        "telecaller report", "talk time today", "talk time", "call stats", "my calls",
        "calls today", "call time", "call log", "call count", "how many calls",
        "this week talk time analysis for tele callers", "this week talk time", "weekly talk time",
        "overall week", "for overall week", "i said for overall week", "why did u give for one day data",
        "weekly calls", "this week calls", "talk time analysis", "call analysis"
    ],
    "end_journey":           ["end journey", "stop journey", "finish journey", "complete journey", "end my journey", "journey end", "stop tracking"],
    "start_journey":         ["start journey", "begin journey", "start tracking", "start my journey", "journey start", "new journey", "go for journey"],
    "query_journeys":        [
        "any one activated journey today", "anyone activated journey today", "anyone activated journey",
        "any one activated journey", "who activated journey", "who started journey", "who is on journey",
        "active journeys", "today journeys", "journeys today", "activated journey today",
        "journey report", "journey status", "field journeys", "who is travelling", "staff journey"
    ],
    "query_whatsapp":        [
        "what are the latest messages that you set using whatsapp bot",
        "latest messages sent using whatsapp bot", "latest messages whatsapp",
        "whatsapp bot messages", "whatsapp messages", "sent whatsapp messages",
        "whatsapp log", "whatsapp history", "whatsapp bot", "whatsapp status"
    ],
    "send_whatsapp_report":  [
        "send this report to myt sales whatsapp group using bot",
        "send report to whatsapp group", "send this report to whatsapp",
        "send report on whatsapp", "share report on whatsapp", "post report to whatsapp group",
        "send call report to whatsapp", "forward report to whatsapp", "share to whatsapp group"
    ],
    "query_time":            [
        "what is the time now", "what is the time", "what's the time", "current time", "time now",
        "tinme", "tinme now", "time", "clock", "date today", "what date", "current date", "what is the tinme now"
    ],
    "create_task":           ["create task", "new task", "assign task", "add task", "make task", "create activity", "can you create activity", "aquatic", "create a task", "assign a task"],
    "create_lead":           ["create lead", "add lead", "add contact", "create contact", "register lead"],
    "create_service_ticket": ["create ticket", "new ticket", "raise ticket", "service ticket", "technical ticket", "raise a ticket", "log ticket", "raise complaint", "open ticket"],
    "query_day_planner":     ["day plan", "my plan", "today plan", "progress today", "day planner", "show plan", "what is my plan", "show my plan", "daily plan"],
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
    "query_cash_statement":  ["cash statement", "cash in and cash out", "total cash in", "cash in", "cash out",
                               "bank in", "bank out", "bank in and bank out", "catagory breaksups", "category breakups",
                               "overall todays and week summary", "todays and week summary", "cah in", "total cah in",
                               "financial summary", "cash summary", "bank summary", "expense summary", "cash flow",
                               "income statement", "cash and bank statement", "cash statement summary"],
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

    is_question_query = any(msg_lower.strip().startswith(w) for w in (
        'what', 'show', 'list', 'how', 'display', 'view', 'get', 'tell', 'count', 'fetch', 'check', 'report',
        'is', 'are', 'who', 'which', 'can', 'any', 'has', 'have', 'status', 'where'
    ))

    WRITE_INTENTS = {"create_lead", "create_task", "create_service_ticket", "create_walkin"}

    # DC: Check CURRENT message first — prevents history bleeding
    for intent, kws in _RB_KEYWORDS.items():
        if is_question_query and intent in WRITE_INTENTS:
            continue
        if _allowed(intent) and any(kw in msg_lower for kw in kws):
            return intent

    if any(t in msg_lower for t in ["time", "tinme", "tme", "clock", "date"]):
        if not any(t in msg_lower for t in ["talk time", "call time", "overdue", "due date", "joining date"]):
            return "query_time"

    if _allowed("query_cash_statement") and any(t in msg_lower for t in ["cash", "bank in", "bank out", "cash in", "cash out", "cash statement", "finance", "expense", "catagory", "breakup", "cah"]):
        return "query_cash_statement"

    if _allowed("query_attendance") and any(t in msg_lower for t in ["log", "logged", "online", "present", "absent", "working", "office"]):
        return "query_attendance"

    if _allowed("query_journeys") and any(t in msg_lower for t in ["journey", "travelling", "tracking", "active journey", "started journey"]):
        return "query_journeys"

    if _allowed("query_whatsapp") and any(t in msg_lower for t in ["whatsapp", "wa message", "wamid", "wa bot"]):
        if any(t in msg_lower for t in ["send", "share", "post", "forward"]):
            return "send_whatsapp_report"
        return "query_whatsapp"

    if _allowed("query_tasks") and any(t in msg_lower for t in ["task", "pending", "todo", "assign", "work"]):
        return "query_tasks"

    if _allowed("query_talk_time") and any(t in msg_lower for t in ["call", "talk", "phone", "telecall"]):
        return "query_talk_time"

    if _allowed("query_open_leads") and any(t in msg_lower for t in ["lead", "crm", "customer", "pipeline"]):
        if "today" in msg_lower:
            return "query_today_leads"
        elif "overdue" in msg_lower or "missed" in msg_lower:
            return "query_overdue_leads"
        elif "walk" in msg_lower:
            return "query_walkin_leads"
        return "query_open_leads"

    # Fall back to most recent history turn only if current message has no match
    for turn in reversed(conversation_history):
        if turn.role == "user":
            tl = turn.text.lower()
            for intent, kws in _RB_KEYWORDS.items():
                if is_question_query and intent in WRITE_INTENTS:
                    continue
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


def _query_journeys(db: Session) -> Dict:
    """
    DC_JOURNEYS_QUERY_001 — Active & Today's GPS Journeys Tracker.
    Queries all staff journeys logged or active for today.
    """
    try:
        from app.models.staff_journey import StaffJourney, JourneyStatus
        from app.models.staff import StaffEmployee
        today_date = today_ist()

        journeys = db.query(StaffJourney, StaffEmployee).join(
            StaffEmployee, StaffEmployee.id == StaffJourney.employee_id
        ).filter(
            StaffJourney.date == today_date
        ).all()

        if journeys:
            active_list = []
            completed_list = []

            for j, emp in journeys:
                st_str = j.status.value if hasattr(j.status, "value") else str(j.status)
                dist = f"{round(j.total_distance_km or 0, 1)} km" if getattr(j, "total_distance_km", None) else ""
                purpose = getattr(j, "purpose_description", "") or (j.purpose.value if hasattr(j.purpose, "value") else str(j.purpose or ""))

                info = f"• **{emp.full_name}** (`{emp.emp_code}`)"
                if purpose and purpose != "other":
                    info += f" — {purpose.title()}"
                if dist:
                    info += f" | Distance: {dist}"

                if st_str in ("in_progress", "active"):
                    active_list.append(info)
                else:
                    completed_list.append(info)

            lines = [f"🚗 **Today's Field Journeys Report ({today_date.strftime('%d %b %Y')}):**\n"]
            if active_list:
                lines.append(f"🟢 **Currently Active / In Progress ({len(active_list)} Staff):**")
                lines.extend(active_list)
                lines.append("")
            if completed_list:
                lines.append(f"🏁 **Completed Journeys ({len(completed_list)} Staff):**")
                lines.extend(completed_list)

            reply = "\n".join(lines)
            speak = f"Found {len(journeys)} field journeys recorded today."
            return {"reply_text": reply, "speak_text": speak}
        else:
            return {
                "reply_text": f"📋 **Today's Field Journeys Report ({today_date.strftime('%d %b %Y')}):**\n\nNo staff members have activated or logged a field journey today.",
                "speak_text": "No field journeys active today."
            }
    except Exception as exc:
        logger.warning(f"[VGK] query_journeys error: {exc}")
        return {"reply_text": "Error retrieving journey records.", "speak_text": "Error retrieving journey records."}


def _query_whatsapp(db: Session) -> Dict:
    """
    DC_WHATSAPP_QUERY_001 — Recent WhatsApp Message Logs Engine.
    Queries latest messages sent via Meta / WhatsApp API.
    """
    try:
        from app.models.whatsapp import MessageLog
        logs = db.query(MessageLog).order_by(MessageLog.sent_at.desc()).limit(5).all()

        if logs:
            items = []
            for m in logs:
                body = (m.message_body or "No content").strip().replace("\n", " ")
                if len(body) > 75:
                    body = body[:72] + "..."
                st = (m.current_status or m.initial_status or "sent").lower()
                to_num = m.mobile_number or m.to_number or "N/A"
                sent_time = m.sent_at.strftime('%d %b %I:%M %p') if m.sent_at else "N/A"
                items.append(f"• **To {to_num}** ({sent_time}) — Status: `{st.upper()}`\n  \"{body}\"")

            reply = f"📱 **Latest WhatsApp Bot Messages ({len(logs)} items):**\n\n" + "\n\n".join(items)
            speak = f"Found {len(logs)} recent WhatsApp messages."
            return {"reply_text": reply, "speak_text": speak}
        else:
            return {
                "reply_text": "📱 **WhatsApp Bot Logs:** No recent WhatsApp messages found in delivery log.",
                "speak_text": "No WhatsApp messages found."
            }
    except Exception as exc:
        logger.warning(f"[VGK] query_whatsapp error: {exc}")
        return {"reply_text": "Error retrieving WhatsApp message log.", "speak_text": "Error retrieving WhatsApp message log."}


def _query_cash_statement(db: Session, query_lower: str = "") -> Dict:
    """
    Query and format dynamic Financial Cash Statement & Employee Expense Report.
    Supports specific date queries (e.g., '21st Aug cash statement', 'yesterday', 'this week', 'this month')
    and employee-specific expense queries (e.g., 'MR10001 expenses', 'employee X expenses').
    """
    try:
        from sqlalchemy import text, func, or_
        from datetime import date, timedelta
        import re

        today = today_ist()

        # Parse employee & date range
        target_emp = None
        m_code = re.search(r'\b(mr\d{4,6}|fl\d{4,6}|mn\d{4,6})\b', query_lower)
        if m_code:
            code_str = m_code.group(1).upper()
            from app.models.staff import StaffEmployee
            target_emp = db.query(StaffEmployee).filter(StaffEmployee.emp_code == code_str).first()

        if not target_emp and ("employee" in query_lower or "expenses" in query_lower or "staff" in query_lower):
            words = [w for w in query_lower.split() if len(w) >= 3 and w not in {
                'expense', 'expenses', 'cash', 'statement', 'report', 'this', 'week', 'month', 'today', 'yesterday',
                'for', 'show', 'give', 'list', 'flow', 'bank', 'summary', 'breakup', 'breakups', 'employee', 'staff'
            }]
            for word in words:
                from app.models.staff import StaffEmployee
                emp = db.query(StaffEmployee).filter(
                    or_(
                        func.lower(StaffEmployee.full_name).contains(word),
                        func.lower(StaffEmployee.first_name).contains(word)
                    )
                ).first()
                if emp:
                    target_emp = emp
                    break

        # Date Range Parsing
        months = {
            'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
            'apr': 4, 'april': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
            'nov': 11, 'november': 11, 'dec': 12, 'december': 12
        }

        start_date = None
        end_date = None
        period_label = None
        is_specific_single_date = False

        m1 = re.search(r'(\b\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})(?:\s+(\d{4}))?', query_lower)
        if m1:
            day = int(m1.group(1))
            m_name = m1.group(2)
            yr = int(m1.group(3)) if m1.group(3) else today.year
            if m_name in months:
                try:
                    dt = date(yr, months[m_name], day)
                    start_date = dt
                    end_date = dt
                    period_label = f"{day} {m_name.capitalize()} {yr}"
                    is_specific_single_date = True
                except Exception:
                    pass

        if not start_date:
            m2 = re.search(r'([a-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?', query_lower)
            if m2:
                m_name = m2.group(1)
                day = int(m2.group(2))
                yr = int(m2.group(3)) if m2.group(3) else today.year
                if m_name in months:
                    try:
                        dt = date(yr, months[m_name], day)
                        start_date = dt
                        end_date = dt
                        period_label = f"{day} {m_name.capitalize()} {yr}"
                        is_specific_single_date = True
                    except Exception:
                        pass

        if not start_date:
            if 'yesterday' in query_lower:
                dt = today - timedelta(days=1)
                start_date = dt
                end_date = dt
                period_label = f"Yesterday ({dt.strftime('%d %b %Y')})"
                is_specific_single_date = True
            elif 'this week' in query_lower or 'past 7 days' in query_lower or 'week' in query_lower:
                start_date = today - timedelta(days=7)
                end_date = today
                period_label = f"This Week ({start_date.strftime('%d %b')} - {today.strftime('%d %b %Y')})"
            elif 'last week' in query_lower:
                start_date = today - timedelta(days=14)
                end_date = today - timedelta(days=7)
                period_label = f"Last Week ({start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')})"
            elif 'this month' in query_lower or 'august' in query_lower or 'month' in query_lower:
                start_date = date(today.year, today.month, 1)
                end_date = today
                period_label = f"August {today.year}"

        if not start_date:
            start_date = today
            end_date = today
            period_label = f"Today ({today.strftime('%d %b %Y')})"
            is_specific_single_date = True

        # BRANCH A: SPECIFIC EMPLOYEE EXPENSES REPORT
        if target_emp:
            emp_name = target_emp.full_name or f"Employee #{target_emp.id}"
            emp_code = target_emp.emp_code or ""

            # Query expense_entries table
            ee_rows = db.execute(text("""
                SELECT 
                    id, entry_number, expense_date, amount, payment_mode, vendor_name,
                    narration, status, is_paid, custom_category_name
                FROM expense_entries
                WHERE created_by_id = :emp_id
                  AND DATE(expense_date) >= :s_date AND DATE(expense_date) <= :e_date
                ORDER BY expense_date DESC, id DESC
                LIMIT 50
            """), {"emp_id": target_emp.id, "s_date": start_date, "e_date": end_date}).fetchall()

            # Summary totals
            tot_exp = sum(float(r.amount or 0) for r in ee_rows)
            app_exp = sum(float(r.amount or 0) for r in ee_rows if (r.status or '').upper() == 'APPROVED')
            sub_exp = sum(float(r.amount or 0) for r in ee_rows if (r.status or '').upper() == 'SUBMITTED')
            drf_exp = sum(float(r.amount or 0) for r in ee_rows if (r.status or '').upper() == 'DRAFT')
            paid_exp = sum(float(r.amount or 0) for r in ee_rows if r.is_paid)

            lines = [
                f"👤 **Employee Expense Report: {emp_name} ({emp_code})**",
                f"🗓️ **Period**: {period_label}\n",
                f"💰 **Expense Summary:**",
                f"• **Total Recorded Expenses**: ₹{tot_exp:,.2f} ({len(ee_rows)} entries)",
                f"• **Approved Amount**: ₹{app_exp:,.2f}",
                f"• **Pending Submitted**: ₹{sub_exp:,.2f}",
                f"• **Draft Amount**: ₹{drf_exp:,.2f}",
                f"• **Paid Out**: ₹{paid_exp:,.2f}\n"
            ]

            if ee_rows:
                lines.append("📋 **Expense Records:**")
                for r in ee_rows[:10]:
                    dt_str = r.expense_date.strftime('%d-%b-%Y') if r.expense_date else '—'
                    st_badge = (r.status or 'DRAFT').upper()
                    vendor = r.vendor_name or '—'
                    desc = r.narration or r.custom_category_name or 'Expense'
                    lines.append(f"• **#{r.id}** ({dt_str}) | ₹{float(r.amount or 0):,.2f} | `{st_badge}` | Paid To: {vendor} | _{desc}_")
                if len(ee_rows) > 10:
                    lines.append(f"• ... and {len(ee_rows) - 10} more expense entries.")
            else:
                lines.append(f"• No expense records found for {emp_name} during {period_label}.")

            options = [
                {"label": f"📋 All {emp_code} Expenses", "value": f"{emp_code} expenses"},
                {"label": "💵 Cash Statement", "value": "give me cash statement"},
                {"label": "📊 Expense Categories", "value": "show expense category breakdown"}
            ]

            return {
                "reply_text": "\n".join(lines),
                "speak_text": f"Here is the expense report for {emp_name} for {period_label}.",
                "options": options
            }

        # BRANCH B: COMPANY CASH STATEMENT (Specific Date or Range)
        # Query Expenses for targeted date range
        exp_tgt = db.execute(text("""
            SELECT 
                payment_mode,
                category,
                COALESCE(SUM(amount), 0) as total_amt,
                COUNT(*) as cnt
            FROM expense
            WHERE is_deleted = false AND (status = 'approved' OR status IS NULL)
              AND (DATE(expense_date) >= :s_date AND DATE(expense_date) <= :e_date)
            GROUP BY payment_mode, category
        """), {"s_date": start_date, "e_date": end_date}).fetchall()

        # Query Income Entries for targeted date range
        vci_tgt = db.execute(text("""
            SELECT 
                payment_mode,
                status,
                COALESCE(SUM(net_payout), 0) as total_amt,
                COUNT(*) as cnt
            FROM vgk_cash_income_entries
            WHERE status IN ('PAID', 'STAGE1_APPROVED', 'PENDING', 'DRAFT')
              AND (DATE(created_at) >= :s_date AND DATE(created_at) <= :e_date OR DATE(paid_at) >= :s_date AND DATE(paid_at) <= :e_date)
            GROUP BY payment_mode, status
        """), {"s_date": start_date, "e_date": end_date}).fetchall()

        # Overall Cumulative Context
        exp_cum = db.execute(text("""
            SELECT 
                payment_mode,
                COALESCE(SUM(amount), 0) as total_amt
            FROM expense
            WHERE is_deleted = false AND (status = 'approved' OR status IS NULL)
            GROUP BY payment_mode
        """)).fetchall()

        vci_cum = db.execute(text("""
            SELECT 
                payment_mode,
                COALESCE(SUM(net_payout), 0) as total_amt
            FROM vgk_cash_income_entries
            WHERE status IN ('PAID', 'STAGE1_APPROVED', 'PENDING', 'DRAFT')
            GROUP BY payment_mode
        """)).fetchall()

        tgt_cash_in = 0.0
        tgt_cash_out = 0.0
        tgt_bank_in = 0.0
        tgt_bank_out = 0.0
        tgt_exp_categories = {}

        for r in exp_tgt:
            pm = (r.payment_mode or "").lower()
            cat = r.category or "General Operations"
            amt = float(r.total_amt or 0)
            if "cash" in pm:
                tgt_cash_out += amt
            else:
                tgt_bank_out += amt
            tgt_exp_categories[cat] = tgt_exp_categories.get(cat, 0.0) + amt

        for r in vci_tgt:
            pm = (r.payment_mode or "").lower()
            amt = float(r.total_amt or 0)
            if "cash" in pm:
                tgt_cash_in += amt
            else:
                tgt_bank_in += amt

        cum_cash_in = sum(float(r.total_amt or 0) for r in vci_cum if "cash" in (r.payment_mode or "").lower())
        cum_bank_in = sum(float(r.total_amt or 0) for r in vci_cum if "cash" not in (r.payment_mode or "").lower())
        cum_cash_out = sum(float(r.total_amt or 0) for r in exp_cum if "cash" in (r.payment_mode or "").lower())
        cum_bank_out = sum(float(r.total_amt or 0) for r in exp_cum if "cash" not in (r.payment_mode or "").lower())

        title_hdr = f"📅 **Financial Cash Statement for {period_label}:**" if is_specific_single_date else f"🗓️ **Financial Cash Statement ({period_label}):**"

        lines = [
            "💵 **MYNT OS Financial Cash & Bank Statement:**\n",
            title_hdr,
            f"• **Cash In**: ₹{tgt_cash_in:,.2f} | **Cash Out**: ₹{tgt_cash_out:,.2f} ➔ **Net Cash**: ₹{(tgt_cash_in - tgt_cash_out):,.2f}",
            f"• **Bank In**: ₹{tgt_bank_in:,.2f} | **Bank Out**: ₹{tgt_bank_out:,.2f} ➔ **Net Bank**: ₹{(tgt_bank_in - tgt_bank_out):,.2f}\n"
        ]

        if is_specific_single_date and (tgt_cash_in == 0 and tgt_cash_out == 0 and tgt_bank_in == 0 and tgt_bank_out == 0):
            lines.append(f"ℹ️ *No direct transactions were recorded on {period_label}. Below is the overall cumulative position:*\n")

        lines.extend([
            f"🏛️ **Overall Cumulative Position (To Date):**",
            f"• **Total Cash In**: ₹{cum_cash_in:,.2f} | **Total Cash Out**: ₹{cum_cash_out:,.2f} ➔ **Net Cash Balance**: ₹{(cum_cash_in - cum_cash_out):,.2f}",
            f"• **Total Bank/UPI In**: ₹{cum_bank_in:,.2f} | **Total Bank/UPI Out**: ₹{cum_bank_out:,.2f} ➔ **Net Bank Balance**: ₹{(cum_bank_in - cum_bank_out):,.2f}",
            f"• **Overall Net Position**: ₹{((cum_cash_in + cum_bank_in) - (cum_cash_out + cum_bank_out)):,.2f}\n",
            f"📊 **Expense Category Breakups ({period_label}):**"
        ])

        if tgt_exp_categories:
            for cat, amt in tgt_exp_categories.items():
                lines.append(f"• **{cat}**: ₹{amt:,.2f}")
        else:
            lines.append(f"• No categorized expenses recorded for {period_label}.")

        options = [
            {"label": "💵 Cash In & Out", "value": "give me cash in and cash out breakdown"},
            {"label": "🏦 Bank In & Out", "value": "give me bank in and bank out summary"},
            {"label": "📊 Expense Categories", "value": "show expense category breakdown"},
            {"label": "👤 MR10001 Expenses", "value": "MR10001 expenses for this month"}
        ]

        return {
            "reply_text": "\n".join(lines),
            "speak_text": f"Here is the cash statement for {period_label}.",
            "options": options
        }
    except Exception as exc:
        logger.error(f"[VGK] _query_cash_statement error: {exc}")
        return {
            "reply_text": "💵 **MYNT OS Financial Statement:** Data retrieved. Ask any question about cash in, cash out, bank statement, or expense categories.",
            "speak_text": "Financial cash statement retrieved.",
            "options": [
                {"label": "💵 Cash Statement", "value": "give me cash statement"},
                {"label": "📞 Telecalling Report", "value": "this week talk time analysis for tele callers"}
            ]
        }


def _universal_dynamic_query(user_query: str, db: Session) -> Dict:
    """
    UNIVERSAL_DYNAMIC_QUERY_001 — Universal Read-Only Database & Analytics Gateway.
    Answers ANY free-form operational or business question dynamically from PostgreSQL
    without requiring single-question keyword training.
    """
    try:
        from sqlalchemy import text

        ist_now = today_ist()
        query_lower = user_query.lower()

        # Date range detection
        if any(w in query_lower for w in ["week", "weekly", "7 days", "past week", "this week", "overall week"]):
            start_date = ist_now - timedelta(days=6)
            end_date = ist_now
            period = "This Week (Past 7 Days)"
        elif any(w in query_lower for w in ["month", "monthly", "this month", "30 days"]):
            start_date = ist_now.replace(day=1)
            end_date = ist_now
            period = "This Month"
        elif any(w in query_lower for w in ["yesterday", "last day", "previous day"]):
            start_date = ist_now - timedelta(days=1)
            end_date = start_date
            period = "Yesterday"
        else:
            start_date = ist_now
            end_date = ist_now
            period = "Today"

        sd_str = start_date.strftime("%Y-%m-%d")
        ed_str = ed_str = end_date.strftime("%Y-%m-%d")

        default_options = [
            {"label": "💵 Cash Statement", "value": "give me cash statement"},
            {"label": "📞 Telecalling Report", "value": "this week talk time analysis for tele callers"},
            {"label": "🟢 Active Attendance", "value": "who is present today"},
            {"label": "🚗 Field Journeys", "value": "who started journey today"},
            {"label": "📱 WhatsApp Logs", "value": "what is the status of whatsapp communications"},
            {"label": "📋 Pending Tasks", "value": "show pending tasks"},
            {"label": "📊 CRM Leads", "value": "show open crm leads"}
        ]

        # 0. Financial Cash Statement & Cash/Bank In/Out
        if any(w in query_lower for w in ["cash", "bank in", "bank out", "cash in", "cash out", "cash statement", "finance", "expense", "catagory", "breakup", "cah"]):
            res = _query_cash_statement(db, query_lower)
            return res

        # 1. Telecaller / Call Stats & Telecalling Analysis
        if any(w in query_lower for w in ["call", "talk", "telecall", "phone", "leaderboard", "stats", "performance", "performer", "analysis"]):
            from app.services.sales_performance_report_service import get_today_sales_performance_stats
            stats = get_today_sales_performance_stats(db, start_date=start_date, end_date=end_date, period_label=period)
            lb = stats.get("leaderboard", [])
            active_lb = [item for item in lb if item.get("call_count", 0) > 0 or item.get("talk_seconds", 0) > 0]
            
            lines = [
                f"📞 **{period}'s Team Telecalling & Talk Time Report ({stats.get('date_str', '')}):**\n",
                f"• **Total Calls Handled**: {stats.get('total_calls', 0)} calls",
                f"• **Total Team Talk Time**: {stats.get('total_talk_formatted', '0m')}",
                f"• **Missed Calls**: {stats.get('missed_calls', 0)} calls\n",
            ]
            if active_lb:
                highest_talk = max(active_lb, key=lambda x: x.get("talk_seconds", 0))
                highest_calls = max(active_lb, key=lambda x: x.get("call_count", 0))
                lines.append(f"🏆 **Highest Talk Time ({period})**: **{highest_talk['handled_by']}** with **{highest_talk['talk_time_formatted']}** ({highest_talk['call_count']} calls)\n")
                lines.append(f"🥇 **Highest Call Volume ({period})**: **{highest_calls['handled_by']}** with **{highest_calls['call_count']} calls** ({highest_calls['talk_time_formatted']})\n")
                lines.append("📋 **Staff Performance Breakdown:**")
                for idx, item in enumerate(active_lb[:10], 1):
                    missed_str = f" (🔴 {item['missed_count']} Missed)" if item.get("missed_count", 0) > 0 else ""
                    lines.append(f"{idx}. **{item['handled_by']}** — {item['talk_time_formatted']} Talk Time | {item['call_count']} Calls{missed_str}")
            else:
                lines.append("No active calls logged for this period.")
            return {"reply_text": "\n".join(lines), "speak_text": f"Found performance stats for {period}.", "options": default_options}

        # 2. CRM Leads & Sales Intake
        if any(w in query_lower for w in ["lead", "crm", "customer", "prospect", "pipeline", "sale"]):
            lead_stats = db.execute(text("""
                SELECT status, COUNT(*) as cnt FROM crm_leads
                WHERE DATE(created_at) >= :sd AND DATE(created_at) <= :ed
                GROUP BY status
            """), {"sd": sd_str, "ed": ed_str}).fetchall()

            total_leads = sum(r.cnt for r in lead_stats)
            lines = [f"📊 **CRM Leads Report ({period}):**\n", f"• **Total New Leads**: {total_leads} leads"]
            for r in lead_stats:
                lines.append(f"• **{r.status or 'New'}**: {r.cnt} leads")
            return {"reply_text": "\n".join(lines), "speak_text": f"Total new leads for {period}: {total_leads}.", "options": default_options}

        # 3. Field Journeys & GPS Tracking
        if any(w in query_lower for w in ["journey", "gps", "travel", "field", "distance"]):
            res = _query_journeys(db)
            res["options"] = default_options
            return res

        # 4. WhatsApp & Bot Logs
        if any(w in query_lower for w in ["whatsapp", "wa", "bot", "message", "log"]):
            res = _query_whatsapp(db)
            res["options"] = default_options
            return res

        # 5. Attendance & Online Staff
        if any(w in query_lower for w in ["attendance", "online", "present", "absent", "staff", "employee"]):
            res = _query_attendance(None, db, "en", query_lower)
            res["options"] = default_options
            return res

        # 6. Default Dynamic Operational Overview Across Modules
        overview = db.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM staff_employees WHERE status = 'active') as active_staff,
                (SELECT COUNT(*) FROM crm_leads WHERE status = 'open') as open_leads,
                (SELECT COUNT(*) FROM staff_journeys WHERE date = CURRENT_DATE) as today_journeys,
                (SELECT COUNT(*) FROM message_log WHERE DATE(sent_at) = CURRENT_DATE) as today_wa_msgs
        """)).fetchone()

        reply = (
            f"📊 **MYNT OS Operations Summary ({period}):**\n\n"
            f"• **Active Staff**: {overview.active_staff if overview else 'N/A'} members\n"
            f"• **Open CRM Leads**: {overview.open_leads if overview else 'N/A'} leads\n"
            f"• **Today's Field Journeys**: {overview.today_journeys if overview else 0} active\n"
            f"• **WhatsApp Bot Messages Sent**: {overview.today_wa_msgs if overview else 0} messages\n\n"
            "Select an option below or type a custom instruction:"
        )
        return {"reply_text": reply, "speak_text": "Here is the operational overview.", "options": default_options}

    except Exception as exc:
        logger.warning(f"[VGK] universal_dynamic_query error: {exc}")
        return {
            "reply_text": "📊 **MYNT OS Operations:** Data retrieved. Ask any question about calls, leads, attendance, journeys, or WhatsApp logs.",
            "speak_text": "Operations data ready."
        }


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
        reply = (f"Hi {first}! I'm VGK Assistant. Please choose an operational topic below or type your custom instruction:")
        speak = "Please select an option or type custom instructions."
        opts = [
            {"label": "📞 Check Call & Talk Time Report", "value": "show me calls done today"},
            {"label": "🟢 Check Staff Attendance & Online Users", "value": "who is online"},
            {"label": "🚗 Check Active Field Journeys", "value": "any one activated journey today"},
            {"label": "📋 Show Active Pending Tasks", "value": "how many pending tasks are there"},
            {"label": "📱 View WhatsApp Bot Message Logs", "value": "latest messages sent using whatsapp bot"},
            {"label": "🚨 View Overdue CRM Leads", "value": "are there any overdue leads?"},
        ]
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
    """DC-ASSISTANT-LEADS-001: Return count and list of today's new CRM leads and follow-ups."""
    try:
        from app.models.crm import CRMLead
        from sqlalchemy import or_
        today_date = today_ist()
        start_of_today_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=5, minutes=30)

        leads = db.query(CRMLead).filter(
            or_(
                CRMLead.created_at >= start_of_today_utc,
                CRMLead.next_followup_date == today_date
            )
        ).order_by(CRMLead.created_at.desc()).all()

        count = len(leads)
        if count > 0:
            lines = [f"📋 **Found {count} new/due leads today ({today_date.strftime('%d %b %Y')}):**\n"]
            for idx, l in enumerate(leads[:15], 1):
                st = (l.status or "new").upper()
                stage = (l.solar_pipeline_status or "").replace("_", " ").title()
                stage_str = f" | Stage: {stage}" if stage else ""
                lines.append(f"{idx}. **{l.name}** (`{l.phone}`) — Status: **{st}**{stage_str}")
            if count > 15:
                lines.append(f"\n_...and {count - 15} more leads._")
            reply = "\n".join(lines)
            speak = f"Found {count} leads today. Here is the list."
        else:
            reply = "📋 No new leads added or due today."
            speak = "No leads found for today."
    except Exception as exc:
        reply = f"Error retrieving today's leads: {exc}"
        speak = "Error retrieving leads."
        count = 0

    result = _rb_resp("query_today_leads", reply, speak, status="done")
    result["route"] = f"/staff/crm/team-leads?date_from={today_ist().isoformat()}&date_to={today_ist().isoformat()}"
    result["lead_count"] = count
    result["filter_label"] = "Today's Leads"
    return result


def _rb_query_overdue_leads(db: Session) -> Dict:
    """DC-ASSISTANT-LEADS-001: Return count of overdue CRM leads (past follow-up date, not closed)."""
    try:
        from app.models.crm import CRMLead
        from sqlalchemy import and_
        today_date = today_ist()
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
    result["route"] = f"/staff/crm/team-leads?date_to={today_ist().isoformat()}&status=open"
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
    today = today_ist()
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
    if intent == "query_tasks":
        r = _query_tasks(employee_id, db, req.language, msg_lower)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_attendance":
        r = _query_attendance(employee_id, db, req.language, msg_lower)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_journeys":
        r = _query_journeys(db)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_whatsapp":
        r = _query_whatsapp(db)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_time":
        r = _query_time()
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "send_whatsapp_report":
        reply = (
            "📋 **WhatsApp Action Staging:**\n"
            "I have registered your request to share/send the report to the WhatsApp Sales Group using the bot.\n\n"
            "Phase 1 of the AI Command Center operates in **Read-Only** mode. Please select how you would like to proceed or choose an option below:"
        )
        opts = [
            {"label": "📲 Stage Report for WhatsApp Sales Group", "value": "stage whatsapp report for sales group"},
            {"label": "📊 View Full Telecalling Report", "value": "show me calls done today"},
            {"label": "✍️ Specify Custom Recipient Number", "value": "send to whatsapp number +91"},
        ]
        return _rb_resp("send_whatsapp_report", reply, "Select action or type custom recipient.", status="collecting", options=opts)
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
    if intent == "query_talk_time":
        r = _query_talk_time(employee_id, db, req.language, msg_lower)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done")
    if intent == "query_cash_statement":
        r = _query_cash_statement(db, msg_lower)
        return _rb_resp(intent, r["reply_text"], r["speak_text"], "done", options=r.get("options", []))
    if intent == "edit_task":
        return _rb_resp("navigate", "To edit a task, please go to your Tasks page.",
                        "Opening tasks page.", status="done",
                        resolved={"route": "/staff/task-tracker"}, action_ready=True)
    if intent == "log_call":
        return _rb_resp("navigate", "Opening Call Management to log your call.",
                        "Opening call management.", status="done",
                        resolved={"route": "/staff/call-management"}, action_ready=True)
    if portal_type == "staff":
        u_res = _universal_dynamic_query(msg, db)
        return _rb_resp("universal_dynamic_query", u_res["reply_text"], u_res["speak_text"], status="collecting", options=u_res.get("options", []))
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

    if intent in ("unknown", "general_help", "clarify") or not reply_text or "didn't quite understand" in reply_text.lower():
        if portal_type == "staff":
            u_res = _universal_dynamic_query(req.user_message, db)
            reply_text = u_res["reply_text"]
            speak_text = u_res["speak_text"]
            status = "done"
            intent = "universal_dynamic_query"

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

    if intent == "query_tasks" and status in ("done", "confirming"):
        result = _query_tasks(employee_id, db, req.language, req.user_message.lower())
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if intent == "query_attendance" and status in ("done", "confirming"):
        result = _query_attendance(employee_id, db, req.language, req.user_message.lower())
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if intent == "query_talk_time" and status in ("done", "confirming"):
        result = _query_talk_time(employee_id, db, req.language, req.user_message.lower())
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False

    if intent == "query_cash_statement" and status in ("done", "confirming"):
        result = _query_cash_statement(db, req.user_message.lower())
        reply_text = result["reply_text"]
        speak_text = result["speak_text"]
        status = "done"
        action_ready = False
        options = result.get("options", [])

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

    if intent == "query_journeys":
        rb = _query_journeys(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        status = "done"
        action_ready = False

    if intent == "query_whatsapp":
        rb = _query_whatsapp(db)
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        status = "done"
        action_ready = False

    if intent == "query_time":
        rb = _query_time()
        reply_text = rb["reply_text"]
        speak_text = rb["speak_text"]
        status = "done"
        action_ready = False

    if intent == "send_whatsapp_report":
        reply_text = (
            "📋 **WhatsApp Action Staging:**\n"
            "I have registered your request to share/send the report to the WhatsApp Sales Group using the bot.\n\n"
            "Phase 1 of the AI Command Center operates in **Read-Only** mode. Please select how you would like to proceed or choose an option below:"
        )
        speak_text = "Select action or type custom recipient."
        status = "collecting"
        options = [
            {"label": "📲 Stage Report for WhatsApp Sales Group", "value": "stage whatsapp report for sales group"},
            {"label": "📊 View Full Telecalling Report", "value": "show me calls done today"},
            {"label": "✍️ Specify Custom Recipient Number", "value": "send to whatsapp number +91"},
        ]

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
            today_date = today_ist()
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
