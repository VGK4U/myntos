"""
MYNT OS — Universal AI Command Center API Gateway
DC Protocol: DC_AI_COMMAND_CENTER_001
Centralized, role-aware, READ-ONLY AI Command Processing Engine
Powered by Gemini NLP + Declarative READ_CAPABILITIES Registry
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os, json, logging, re
from datetime import datetime, date, timedelta
import pytz

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.audit import AuditLogger
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.api.v1.endpoints.partner_auth import get_current_partner
from app.models.staff import StaffEmployee
from app.models.staff_accounts import OfficialPartner
from app.models.staff_tasks import StaffTask
from app.models.call_tracking import StaffCallLog as CallLog

# Import pingme NLP processor & handlers
from app.api.v1.endpoints.pingme import (
    _process, _rb_detect_intent, _rb_marketplace_search, _rb_general_help,
    VGKRequest, VGKResponse, IST, today_ist
)

router = APIRouter(prefix="/ai", tags=["AI Command Center"])


# ─── Declarative READ_CAPABILITIES Registry ──────────────────────────────────────

READ_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "query_attendance": {
        "capability_name": "query_attendance",
        "description": "Retrieve today's attendance status, check-in time, and location verification for authenticated employee.",
        "allowed_roles": ["STAFF", "OPERATIONS", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["What is my attendance today?", "Am I clocked in?"]
    },
    "query_tasks": {
        "capability_name": "query_tasks",
        "description": "Retrieve assigned tasks, pending deadlines, and priority items for authenticated employee.",
        "allowed_roles": ["STAFF", "OPERATIONS", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Show my pending tasks", "What are my tasks for today?"]
    },
    "query_talk_time": {
        "capability_name": "query_talk_time",
        "description": "Retrieve total calls made, total talk time, and telecalling performance metrics for today.",
        "allowed_roles": ["STAFF", "TELECALLER", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["What is my talk time today?", "Show my call report"]
    },
    "query_open_leads": {
        "capability_name": "query_open_leads",
        "description": "Retrieve open CRM leads, customer contacts, and active pipeline items.",
        "allowed_roles": ["STAFF", "TELECALLER", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Show my open CRM leads", "List open leads"]
    },
    "query_today_leads": {
        "capability_name": "query_today_leads",
        "description": "Retrieve CRM leads created or assigned today.",
        "allowed_roles": ["STAFF", "TELECALLER", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Show today's leads", "How many leads arrived today?"]
    },
    "query_overdue_leads": {
        "capability_name": "query_overdue_leads",
        "description": "Retrieve CRM leads with overdue follow-ups or missed contact dates.",
        "allowed_roles": ["STAFF", "TELECALLER", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Show overdue leads", "Which leads need immediate follow-up?"]
    },
    "query_walkin_leads": {
        "capability_name": "query_walkin_leads",
        "description": "Retrieve walk-in customer leads registered at branch offices.",
        "allowed_roles": ["STAFF", "TELECALLER", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Show walk-in leads", "List office walk-ins"]
    },
    "query_partner_activity": {
        "capability_name": "query_partner_activity",
        "description": "Retrieve network partner earnings, referral performance, and team summary.",
        "allowed_roles": ["PARTNER"],
        "required_params": [],
        "sample_queries": ["What are my earnings this month?", "Show my partner performance"]
    },
    "marketplace_search": {
        "capability_name": "marketplace_search",
        "description": "Search available catalog products, pricing, solar packages, and EV vouchers.",
        "allowed_roles": ["PUBLIC", "STAFF", "PARTNER", "ADMIN"],
        "required_params": ["query"],
        "sample_queries": ["Search solar packages", "Show EV products"]
    },
    "navigate": {
        "capability_name": "navigate",
        "description": "Resolve requested screen or dashboard route and provide quick navigation link.",
        "allowed_roles": ["PUBLIC", "STAFF", "PARTNER", "ADMIN"],
        "required_params": ["target_route"],
        "sample_queries": ["Take me to CRM dashboard", "Open my timesheet"]
    },
    "query_cash_statement": {
        "capability_name": "query_cash_statement",
        "description": "Retrieve financial cash statement including Cash In, Cash Out, Bank In, Bank Out, and category breakups for Today, This Week, and Overall.",
        "allowed_roles": ["STAFF", "OPERATIONS", "TEAM_LEAD", "ADMIN"],
        "required_params": [],
        "sample_queries": ["Give me the cash statement", "Total cash in and cash out summary", "Bank and bank out category breakups"]
    }
}


# ─── Pydantic Request / Response Models ───────────────────────────────────────

class CommandProcessRequest(BaseModel):
    user_message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: List[Dict[str, str]] = Field(default=[])
    language: str = Field(default="en")
    portal_type: str = Field(default="staff", description="staff | partner | public")
    company_id: Optional[int] = 1


class CommandCapabilitiesResponse(BaseModel):
    success: bool = True
    total_capabilities: int
    capabilities: List[Dict[str, Any]]
    phase: str = "PHASE_1_READ_ONLY"


# ─── Capabilities Endpoint ───────────────────────────────────────────────────

@router.get("/command/capabilities", response_model=CommandCapabilitiesResponse)
async def get_command_capabilities():
    """
    Returns list of registered READ-ONLY capabilities for the Universal AI Command Center.
    """
    caps_list = list(READ_CAPABILITIES.values())
    return CommandCapabilitiesResponse(
        success=True,
        total_capabilities=len(caps_list),
        capabilities=caps_list,
        phase="PHASE_1_READ_ONLY"
    )


# ─── Command Process Gateway Endpoint ────────────────────────────────────────

@router.post("/command/process", response_model=VGKResponse)
async def process_ai_command(
    req: CommandProcessRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Universal AI Command Gateway
    Supports Staff, Partner, and Public command contexts with strict JWT RBAC and Audit Logging.
    PHASE 1: Strictly READ-ONLY processing. Write actions are staged with clear notification.
    """
    portal_type = req.portal_type.lower()
    current_staff = None
    current_partner = None

    # Authenticate based on Portal Context & Bearer Header
    raw_token = authorization if isinstance(authorization, str) else (request.headers.get("authorization") or request.headers.get("Authorization") or "")
    token = raw_token.strip()
    while token.lower().startswith("bearer "):
        token = token[7:].strip()
    token = token.strip('"').strip("'")

    print(f"[AI_GATEWAY_DEBUG] raw_token: '{raw_token}', parsed token length: {len(token)}", flush=True)

    if token:
        from jose import jwt
        from app.core.config import settings

        if portal_type == "partner":
            try:
                current_partner = get_current_partner(request=request, db=db)
            except Exception:
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    pid = payload.get("sub") or payload.get("partner_id")
                    if pid and str(pid).isdigit():
                        current_partner = db.query(OfficialPartner).filter_by(id=int(pid)).first()
                except Exception as pe:
                    print(f"[AI_GATEWAY_DEBUG] Partner decode error: {pe}", flush=True)
                    current_partner = None
        else:
            try:
                current_staff = get_current_staff_user(request=request, db=db)
            except Exception as se1:
                print(f"[AI_GATEWAY_DEBUG] get_current_staff_user failed: {se1}", flush=True)
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    print(f"[AI_GATEWAY_DEBUG] decoded payload: {payload}", flush=True)
                    eid = payload.get("sub") or payload.get("employee_id") or payload.get("user_id")
                    code = payload.get("emp_code")
                    if eid and str(eid).isdigit():
                        current_staff = db.query(StaffEmployee).filter_by(id=int(eid)).first()
                    elif code:
                        current_staff = db.query(StaffEmployee).filter_by(emp_code=str(code)).first()
                except Exception as se2:
                    print(f"[AI_GATEWAY_DEBUG] Staff decode fallback error: {se2}", flush=True)
                    current_staff = None

    print(f"[AI_GATEWAY_DEBUG] Resolved current_staff: {current_staff}", flush=True)

    # Fallback / Enforcement
    if portal_type == "staff" and not current_staff:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login to use Staff AI Command Center."
        )
    elif portal_type == "partner" and not current_partner:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please login to use Partner AI Command Center."
        )

    # Convert request format for pingme engine
    vgk_req = VGKRequest(
        user_message=req.user_message,
        conversation_history=[{"role": turn.get("role", "user"), "text": turn.get("text", "")} for turn in req.conversation_history],
        language=req.language,
        company_id=req.company_id
    )

    user_name = "Guest User"
    emp_code = "PUBLIC"
    employee_id = None
    partner_id = None

    if current_staff:
        user_name = current_staff.full_name or current_staff.emp_code or "Staff Member"
        emp_code = current_staff.emp_code
        employee_id = current_staff.id
    elif current_partner:
        user_name = current_partner.partner_name or current_partner.partner_code or "Partner"
        emp_code = current_partner.partner_code
        partner_id = current_partner.id

    # Execute intent resolution & ORM data fetch via core process helper
    response = await _process(
        req=vgk_req,
        portal_type=portal_type if (current_staff or current_partner) else "marketplace",
        user_name=user_name,
        emp_code=emp_code,
        employee_id=employee_id,
        partner_id=partner_id,
        db=db
    )

    # PHASE 1 ENFORCEMENT: Override any write intent attempts to remain strictly READ-ONLY
    WRITE_INTENTS = {"create_task", "create_lead", "create_service_ticket", "create_walkin"}
    if response.intent in WRITE_INTENTS or response.action_ready:
        response.action_ready = False
        response.action_type = None
        response.status = "read_only_restricted"
        response.reply_text = (
            f"I have understood your request to perform '{response.intent.replace('_', ' ').title()}'. "
            "Phase 1 of the AI Command Center is strictly READ-ONLY for security compliance. "
            "Automated action execution will be enabled in Phase 2 with full confirmation controls."
        )
        response.speak_text = response.reply_text

    # Log query execution in Audit Trail
    try:
        AuditLogger.log_action(
            db=db,
            user=current_staff or current_partner or "PUBLIC_USER",
            action="AI_COMMAND_QUERY",
            resource_type="AI_COMMAND_CENTER",
            details={
                "portal_type": portal_type,
                "raw_message": req.user_message,
                "resolved_intent": response.intent,
                "status": response.status,
                "phase": "PHASE_1_READ_ONLY"
            },
            ip_address=request.client.host if request.client else None
        )
    except Exception as e:
        logger.warning(f"[AI_COMMAND_CENTER] Failed to record audit log: {e}")

    return response
