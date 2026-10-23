"""
VGK Member Quick Alerts API Endpoints
Handles one-click application & support alerts from the VGK4U member portal.
Includes staff atomic claim locks, 3-hour re-claim SLA, WhatsApp group dispatch, and status tracking.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc

from app.core.database import get_db
from app.models.staff_accounts import OfficialPartner, AssociatedCompany
from app.models.staff import StaffEmployee
from app.models.vgk_quick_alert import VGKMemberQuickAlert
from app.api.v1.endpoints.vgk_auth import get_current_vgk_member
from app.api.v1.endpoints.staff_auth import get_current_staff_user
from app.services.whatsapp_group_alert_service import send_group_bot_message
from app.core.timezone import get_indian_time

logger = logging.getLogger(__name__)

router = APIRouter()

THREE_HOURS_SECONDS = 10800  # 3 hours = 10,800 seconds


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class QuickAlertImageItem(BaseModel):
    filename: Optional[str] = "support_image.jpg"
    content_type: Optional[str] = "image/jpeg"
    data_base64: str = Field(..., description="Base64 or Data URL string of the image")


class QuickAlertCreateRequest(BaseModel):
    alert_type: str = Field(..., description="'APPLICATION' or 'SUPPORT'")
    notes: Optional[str] = Field(None, description="Optional brief customer notes or requirement")
    priority: Optional[str] = Field("High", description="Priority level")
    issue_category: Optional[str] = Field(None, description="Support ticket issue category")
    reason: Optional[str] = Field(None, description="Support ticket reason / subject")
    details: Optional[str] = Field(None, description="Detailed description of issue")
    images: Optional[List[QuickAlertImageItem]] = Field(None, description="Optional base64 images for support ticket")


class QuickAlertUpdateRequest(BaseModel):
    token: str = Field(..., description="Alert claim token")
    status: str = Field(..., description="'IN_PROGRESS' or 'PROCESSED' or 'CANCELLED'")
    notes: Optional[str] = Field(None, description="Staff processing or completion notes")
    linked_crm_lead_id: Optional[int] = None
    linked_ticket_id: Optional[int] = None


class QuickAlertClaimRequest(BaseModel):
    token: str = Field(..., description="Alert claim token")


class QuickAlertMemberCancelRequest(BaseModel):
    alert_id: Optional[int] = None
    token: Optional[str] = None
    reason: Optional[str] = None


# ─── Helper Functions ─────────────────────────────────────────────────────────

def is_staff_eligible_for_quick_alerts(user: StaffEmployee) -> bool:
    """
    Returns True if the logged-in staff member belongs to the Sales Department
    or holds a Key Leadership / Admin role.
    """
    if not user:
        return False

    # DC Protocol: SaaS Multi-Tenant Isolation
    # Non-platform / SaaS tenant staff are strictly NOT eligible for internal VGK alerts
    tenant_id = getattr(user, "tenant_id", 1) or 1
    staff_type = (getattr(user, "staff_type", "") or "").upper().strip()
    role_code_raw = (getattr(getattr(user, "role", None), "role_code", "") or "").lower().strip()
    company_segment = (getattr(getattr(user, "base_company", None), "company_segment", "") or getattr(user, "company_segment", "") or "").upper().strip()
    
    if tenant_id != 1 or staff_type in ("TENANT_ADMIN", "SAAS_CLIENT", "SAAS_TENANT") or role_code_raw == "tenant_admin" or company_segment == "SEGMENT_B_SAAS":
        return False

    role_code = ""
    role_name = ""
    if getattr(user, "role", None):
        role_code = (getattr(user.role, "role_code", "") or "").lower().strip()
        role_name = (getattr(user.role, "role_name", "") or "").upper().strip()

    dept_name = ""
    dept_code = ""
    if getattr(user, "department", None):
        dept_name = (getattr(user.department, "name", "") or "").lower().strip()
        dept_code = (getattr(user.department, "department_code", "") or "").lower().strip()

    leadership_codes = {
        "vgk4u", "vgk4u_supreme", "key_leadership", "leadership_role",
        "ea", "executive_admin", "super_admin", "admin"
    }
    leadership_names = {
        "VGK4U", "VGK MENTOR", "VGK4U SUPREME", "KEY LEADERSHIP",
        "LEADERSHIP ROLE", "EA", "EXECUTIVE ADMIN", "SUPER ADMIN"
    }

    if role_code in leadership_codes or "vgk4u" in role_code or role_name in leadership_names:
        return True

    if "sales" in dept_name or "crm" in dept_name or "sales" in dept_code or "crm" in dept_code:
        return True

    emp_code = (getattr(user, "emp_code", "") or "").upper().strip()
    if emp_code == "MR10001":
        return True

    return False


def generate_alert_code(alert_type: str) -> str:
    """Generate unique tracking code like VQA-APP-20261013-A8F2"""
    ist_now = get_indian_time()
    date_str = ist_now.strftime("%Y%m%d")
    prefix = "APP" if "APP" in alert_type.upper() else "SUP"
    rand_suffix = uuid.uuid4().hex[:4].upper()
    return f"VQA-{prefix}-{date_str}-{rand_suffix}"


def format_whatsapp_alert_message(alert: VGKMemberQuickAlert, claim_url: str) -> str:
    """Build high-visibility WhatsApp broadcast message with one-click claim link"""
    ist_now = get_indian_time()
    time_str = ist_now.strftime("%d %b %Y, %I:%M %p IST")

    is_app = (alert.alert_type == "APPLICATION")
    if is_app:
        title = "⚡ *NEW VGK4U MEMBER APPLICATION ALERT!* ⚡"
        type_label = "APPLICATION"
    else:
        title = "🆘 *VGK4U MEMBER SUPPORT REQUEST!* 🆘"
        type_label = "SUPPORT"

    notes_str = f'"{alert.notes.strip()}"' if alert.notes and alert.notes.strip() else "_No additional notes provided._"

    lines = [
        title,
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 *Channel Partner*: {alert.partner_name}",
        f"🆔 *Partner Code*: {alert.partner_code}",
        f"📱 *Mobile*: +91 {alert.partner_phone.replace('+91', '').strip()}",
        f"⏰ *Submitted At*: {time_str}",
        f"📋 *Request Type*: {type_label}",
        f"💬 *Details*: {notes_str}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "👉 *CLICK TO CLAIM THIS REQUEST*:",
        f"🔗 {claim_url}",
        "*(First staff to click will claim; if pending >3 hours, any Sales/Leadership staff can re-claim)*"
    ]
    return "\n".join(lines)


def dispatch_quick_alert_to_whatsapp_groups(
    db: Session,
    message_text: str,
    job_id: str = "vgk_member_quick_alert",
    job_name: str = "VGK4U Member Quick Alert Broadcast",
    trigger_type: str = "quick_alert",
    idempotency_prefix: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolves active Sales WhatsApp Group targets from AutomationTargetConfig
    (including 'wa_bihourly_sales_perf_report' and 'vgk_member_quick_alert' targets)
    plus the canonical 'Mynt Sales New' group, and dispatches with full execution tracking
    and automatic invite/group-name fallback resolution.
    """
    target_list = []
    seen_identifiers = set()

    try:
        from app.services.automation_tracking_service import get_job_targets
        for cfg_job_id in ("vgk_member_quick_alert", "wa_bihourly_sales_perf_report"):
            cfg_targets = get_job_targets(db, cfg_job_id, company_id=1, active_only=True)
            for t in (cfg_targets or []):
                ident = (getattr(t, "identifier", None) or (t.get("identifier") if isinstance(t, dict) else "") or "").strip()
                t_name = (getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "") or "Mynt Sales New").strip()
                t_type = (getattr(t, "target_type", None) or (t.get("target_type") if isinstance(t, dict) else "group") or "group").strip()
                if ident and ident not in seen_identifiers:
                    seen_identifiers.add(ident)
                    target_list.append({
                        "target_type": t_type,
                        "name": t_name,
                        "identifier": ident
                    })
    except Exception as cfg_err:
        logger.warning(f"[VGK-ALERT] Target config lookup note: {cfg_err}")

    # Always ensure canonical Mynt Sales New group is present
    canonical_jid = "120363410784518818@g.us"
    if canonical_jid not in seen_identifiers and "LfX8mGootXa7SpwNIz7P5C" not in seen_identifiers:
        target_list.append({
            "target_type": "group",
            "name": "Mynt Sales New",
            "identifier": canonical_jid
        })

    execution = None
    try:
        from app.services.automation_tracking_service import create_execution, record_dispatch, finalize_execution
        summary_str = ", ".join(t["name"] for t in target_list)
        execution = create_execution(
            db=db,
            job_id=job_id,
            job_name=job_name,
            trigger_type=trigger_type.upper(),
            triggered_by="VGK4U Member Portal",
            target_summary=summary_str
        )
    except Exception as exec_err:
        logger.warning(f"[VGK-ALERT] Execution tracking init note: {exec_err}")

    dispatched_any = False
    results = []
    for tg in target_list:
        ident = tg["identifier"]
        is_jid = "@g.us" in ident
        # Pass invite_code fallback for Mynt Sales New so bot can resolve by JID, groupName, or inviteCode
        inv_code = "LfX8mGootXa7SpwNIz7P5C" if (ident == canonical_jid or tg["name"] == "Mynt Sales New") else ("" if is_jid else ident)
        idem_key = f"{idempotency_prefix}_{ident}" if idempotency_prefix else None

        try:
            res = send_group_bot_message(
                message_text=message_text,
                invite_code=inv_code,
                group_name=tg["name"],
                group_id=ident if is_jid else None,
                job_id=job_id,
                job_name=job_name,
                trigger_type=trigger_type,
                db=db,
                execution_id=execution.id if execution else None,
                idempotency_key=idem_key
            )
            results.append(res)
            is_succ = isinstance(res, dict) and res.get("success") is True and not res.get("queued")
            is_queued = isinstance(res, dict) and res.get("queued") is True
            if is_succ or is_queued:
                dispatched_any = True

            if execution:
                from app.services.automation_tracking_service import record_dispatch
                d_status = "SENT" if is_succ else ("QUEUED" if is_queued else "FAILED")
                d_err = res.get("error") if not (is_succ or is_queued) else None
                record_dispatch(
                    db=db,
                    execution_id=execution.id,
                    job_id=job_id,
                    recipient_type="GROUP",
                    recipient_identifier=ident,
                    recipient_name=tg["name"],
                    queue_id=res.get("queue_id"),
                    provider="BOT_GATEWAY",
                    status=d_status,
                    error_message=d_err
                )
        except Exception as send_err:
            logger.warning(f"[VGK-ALERT] Group dispatch error for {tg['name']}: {send_err}")
            results.append({"success": False, "error": str(send_err)})

    if execution:
        try:
            from app.services.automation_tracking_service import finalize_execution
            finalize_execution(db=db, execution_id=execution.id)
        except Exception:
            pass

    return {"success": dispatched_any, "results": results}


def _resolve_uploads_root() -> str:
    import os
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
    media_backup = os.path.join(workspace_root, "media_backup")
    if os.path.exists(media_backup):
        return media_backup
    backend_uploads = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))
    os.makedirs(backend_uploads, exist_ok=True)
    return backend_uploads


def _save_support_ticket_images(
    db: Session,
    ticket_id: int,
    partner_id: int,
    images: Optional[List[QuickAlertImageItem]]
) -> List[Dict[str, Any]]:
    if not images:
        return []
    import os
    import base64
    from app.models.ticket import TicketAttachment

    saved_list = []
    uploads_root = _resolve_uploads_root()
    rel_dir = f"service_ticket_media/{ticket_id}"
    abs_dir = os.path.join(uploads_root, "service_ticket_media", str(ticket_id))
    os.makedirs(abs_dir, exist_ok=True)

    for idx, img_item in enumerate(images[:5]):
        try:
            raw_b64 = (img_item.data_base64 or "").strip()
            if not raw_b64:
                continue
            mime_type = img_item.content_type or "image/jpeg"
            if "," in raw_b64 and raw_b64.startswith("data:"):
                header, raw_b64 = raw_b64.split(",", 1)
                if ";" in header and ":" in header:
                    mime_type = header.split(":", 1)[1].split(";", 1)[0] or mime_type

            img_bytes = base64.b64decode(raw_b64)
            if not img_bytes or len(img_bytes) > 10 * 1024 * 1024:
                continue

            orig_name = os.path.basename(img_item.filename or f"support_{idx+1}.jpg")
            ext = os.path.splitext(orig_name)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"

            safe_name = f"sup_{ticket_id}_{idx+1}_{uuid.uuid4().hex[:6]}{ext}"
            rel_path = f"{rel_dir}/{safe_name}"
            abs_path = os.path.join(abs_dir, safe_name)

            with open(abs_path, "wb") as f:
                f.write(img_bytes)

            try:
                from app.services.object_storage import storage_service
                storage_service.upload_file(f"uploads/{rel_path}", img_bytes)
            except Exception:
                pass

            att = TicketAttachment(
                ticket_id=ticket_id,
                file_path=f"/uploads/{rel_path}",
                original_filename=orig_name,
                file_size=len(img_bytes),
                mime_type=mime_type,
                media_type="image",
                uploaded_by_partner_id=partner_id,
                uploaded_at=get_indian_time(),
                processing_status="completed"
            )
            db.add(att)
            db.flush()
            saved_list.append({
                "id": att.id,
                "filename": orig_name,
                "url": f"/uploads/{rel_path}"
            })
        except Exception as img_err:
            logger.warning(f"[VGK-ALERT] Image save warning for ticket #{ticket_id}: {img_err}")

    return saved_list


def sync_linked_service_ticket(
    db: Session,
    alert: VGKMemberQuickAlert,
    new_alert_status: Optional[str] = None,
    actor_name: str = "",
    notes: Optional[str] = None,
    staff_id: Optional[int] = None,
    new_status: Optional[str] = None
) -> None:
    """Synchronize VGKMemberQuickAlert status changes with the Service Module (ServiceTicket)."""
    target_status = (new_status or new_alert_status or "").strip().upper()
    if not alert.linked_ticket_id or not target_status:
        return
    try:
        from app.models.ticket import ServiceTicket, TicketLog
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == alert.linked_ticket_id).first()
        if not ticket:
            return

        now_ist = get_indian_time()
        old_status = ticket.status

        if target_status in ("CLAIMED", "IN_PROGRESS"):
            ticket.status = "In Progress"
            ticket.sub_status = "acknowledged"
            if not ticket.in_progress_date:
                ticket.in_progress_date = now_ist
            if staff_id and not ticket.service_manager_id:
                ticket.service_manager_id = staff_id
        elif target_status == "WAITING_FOR_DETAILS":
            ticket.status = "Waiting on Customer"
            ticket.sub_status = "awaiting_details"
            if notes:
                ticket.admin_response = f"Waiting for details: {notes}"
        elif target_status == "PROCESSED":
            ticket.status = "Resolved"
            ticket.sub_status = "work_complete"
            ticket.resolved_date = now_ist
            ticket.work_completed_at = now_ist
            if notes:
                ticket.resolution_summary = notes
        elif target_status == "CANCELLED":
            ticket.status = "Closed"
            ticket.sub_status = "closed"
            ticket.closed_date = now_ist
            if notes:
                ticket.resolution_summary = f"Cancelled: {notes}"

        ticket.last_response_date = now_ist
        if notes:
            ticket.admin_response = notes

        log_entry = TicketLog(
            ticket_id=ticket.id,
            action_type=f"Status -> {ticket.status}",
            action_description=f"[{actor_name}] {notes or target_status}",
            performed_at=now_ist,
            old_value=old_status,
            new_value=ticket.status
        )
        db.add(log_entry)
    except Exception as sync_err:
        logger.warning(f"[VGK-ALERT] ServiceTicket sync note: {sync_err}")


def enrich_alerts_with_service_tickets(db: Session, alert_dicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach ServiceTicket metadata (ticket_id, category, reason, details, attachments) to alert dicts."""
    if not alert_dicts:
        return alert_dicts

    ticket_ids = [d["linked_ticket_id"] for d in alert_dicts if d.get("linked_ticket_id")]
    ticket_map: Dict[int, Any] = {}
    att_map: Dict[int, List[Dict[str, Any]]] = {}

    if ticket_ids:
        try:
            from app.models.ticket import ServiceTicket, TicketAttachment
            tickets = db.query(ServiceTicket).filter(ServiceTicket.id.in_(ticket_ids)).all()
            for t in tickets:
                ticket_map[t.id] = t

            atts = db.query(TicketAttachment).filter(TicketAttachment.ticket_id.in_(ticket_ids)).all()
            for a in atts:
                fp = a.file_path or ""
                url = fp if fp.startswith("/") or fp.startswith("http") else f"/uploads/{fp.lstrip('/')}"
                att_map.setdefault(a.ticket_id, []).append({
                    "id": a.id,
                    "filename": a.original_filename,
                    "url": url
                })
        except Exception as e:
            logger.warning(f"[VGK-ALERT] Ticket enrichment note: {e}")

    for d in alert_dicts:
        tid = d.get("linked_ticket_id")
        t_obj = ticket_map.get(tid) if tid else None

        # Parse structured Category / Reason / Details if present in notes
        raw_notes = d.get("notes") or ""
        parsed_cat = None
        parsed_reason = None
        parsed_details = raw_notes
        if raw_notes.startswith("[Category:"):
            try:
                first_line, _, rest = raw_notes.partition("\n")
                parsed_details = rest.strip() or raw_notes
                inner = first_line.strip("[]")
                for part in inner.split("|"):
                    k, _, v = part.partition(":")
                    k_clean = k.strip().lower()
                    if "category" in k_clean:
                        parsed_cat = v.strip()
                    elif "reason" in k_clean:
                        parsed_reason = v.strip()
            except Exception:
                pass

        d["issue_category"] = (t_obj.issue_category if t_obj else None) or parsed_cat
        d["issue_reason"] = parsed_reason
        d["issue_details"] = parsed_details
        d["linked_ticket_code"] = t_obj.ticket_id if t_obj else None
        d["service_ticket_status"] = t_obj.status if t_obj else None
        d["service_ticket_sub_status"] = t_obj.sub_status if t_obj else None
        d["attachments"] = att_map.get(tid, []) if tid else []

    return alert_dicts


_SVC_COUNTS_CACHE: Dict[str, Any] = {"timestamp": 0.0, "data": None}


def get_service_module_counts(db: Session) -> Dict[str, int]:
    """Query live Service Module (ServiceTicket) counts with 30s in-memory cache and single-pass aggregation."""
    import time
    now_ts = time.time()
    if _SVC_COUNTS_CACHE.get("data") and (now_ts - _SVC_COUNTS_CACHE["timestamp"]) < 30.0:
        return dict(_SVC_COUNTS_CACHE["data"])

    try:
        from app.models.ticket import ServiceTicket
        from sqlalchemy import func, case, or_
        row = db.query(
            func.count(ServiceTicket.id),
            func.count(case([(ServiceTicket.status == "Open", 1)])),
            func.count(case([(ServiceTicket.status.in_(["Assigned", "In Progress"]), 1)])),
            func.count(case([(ServiceTicket.status.in_(["Resolved", "Closed"]), 1)])),
            func.count(case([(or_(ServiceTicket.partner_id.isnot(None), ServiceTicket.source_channel == "partner_portal"), 1)]))
        ).first()

        res = {
            "total_tickets": int(row[0] or 0) if row else 0,
            "open_tickets": int(row[1] or 0) if row else 0,
            "in_progress_tickets": int(row[2] or 0) if row else 0,
            "resolved_tickets": int(row[3] or 0) if row else 0,
            "partner_support_tickets": int(row[4] or 0) if row else 0
        }
        _SVC_COUNTS_CACHE["timestamp"] = now_ts
        _SVC_COUNTS_CACHE["data"] = res
        return res
    except Exception as e:
        logger.warning(f"[VGK-ALERT] Service module count query note: {e}")
        return dict(_SVC_COUNTS_CACHE.get("data") or {
            "total_tickets": 0,
            "open_tickets": 0,
            "in_progress_tickets": 0,
            "resolved_tickets": 0,
            "partner_support_tickets": 0
        })


# ─── Member Endpoints ─────────────────────────────────────────────────────────

@router.post("/create")
def create_member_quick_alert(
    payload: QuickAlertCreateRequest,
    request: Request,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    1-Click instant Application alert OR structured Support Ticket from VGK4U member portal.
    - When alert_type == 'SUPPORT', creates a ServiceTicket in the Service Module (with optional image uploads)
      and links it via linked_ticket_id so it is tracked in the Service Module while showing counts & status on /staff/progress.
    - Dispatches alert to Sales Team WhatsApp group with staff claim link.
    """
    raw_type = payload.alert_type.upper().strip()
    if raw_type not in ("APPLICATION", "IMMEDIATE_SUPPORT", "SUPPORT"):
        raise HTTPException(status_code=400, detail="Invalid alert_type. Must be APPLICATION or SUPPORT")

    alert_type = "APPLICATION" if raw_type == "APPLICATION" else "SUPPORT"
    alert_code = generate_alert_code(alert_type)
    claim_token = uuid.uuid4().hex
    now_ist = get_indian_time()

    # Clean phone
    phone = (current_member.phone or "").strip()
    if not phone and hasattr(current_member, "mobile_number"):
        phone = (current_member.mobile_number or "").strip()

    # Partner name
    partner_name = (
        getattr(current_member, "partner_name", None) or
        getattr(current_member, "name", None) or
        f"Partner {current_member.partner_code}"
    ).strip()

    # Build notes & create ServiceTicket in Service Module if SUPPORT
    linked_ticket_id = None
    linked_ticket_code = None
    saved_attachments: List[Dict[str, Any]] = []

    raw_details = (payload.details or payload.notes or "").strip()
    issue_cat = (payload.issue_category or "").strip()
    issue_reason = (payload.reason or "").strip()

    if alert_type == "SUPPORT":
        cat_label = issue_cat or "Partner Support"
        reason_label = issue_reason or "Support Assistance"
        header_tag = f"[Category: {cat_label} | Reason: {reason_label}]"
        formatted_notes = f"{header_tag}\n{raw_details}".strip() if raw_details else header_tag

        try:
            from app.models.ticket import ServiceTicket, TicketLog
            from app.services.ticket_service import TicketService

            t_code = TicketService.generate_ticket_id(db=db)
            sla_due = now_ist + timedelta(hours=24)
            t_type = "technical" if any(k in cat_label.lower() for k in ("solar", "ev", "inverter", "technical")) else "general"

            svc_ticket = ServiceTicket(
                ticket_id=t_code,
                company_id=current_member.company_id,
                tenant_id=getattr(current_member, "tenant_id", None),
                partner_id=current_member.id,
                source_channel="partner_portal",
                ticket_type=t_type,
                sub_status="new",
                issue_category=cat_label,
                issue_description=f"Reason: {reason_label}\nDetails: {raw_details or 'N/A'}\nAlert Ref: {alert_code}",
                priority=payload.priority or "High",
                status="Open",
                created_date=now_ist,
                sla_deadline=sla_due,
                sla_status="Within SLA",
                tat_committed_at=now_ist,
                tat_due_at=sla_due,
                tat_base_hours=24,
                customer_name=partner_name,
                customer_phone=phone,
                ip_address=request.client.host if request.client else None,
                user_agent=(request.headers.get("user-agent") or "")[:200]
            )
            db.add(svc_ticket)
            db.flush()

            linked_ticket_id = svc_ticket.id
            linked_ticket_code = svc_ticket.ticket_id

            t_log = TicketLog(
                ticket_id=svc_ticket.id,
                action_type="Created",
                action_description=f"Support ticket raised by VGK4U Partner {partner_name} ({current_member.partner_code}) — {cat_label}: {reason_label}",
                performed_at=now_ist,
                new_value="Open"
            )
            db.add(t_log)

            if payload.images:
                saved_attachments = _save_support_ticket_images(
                    db=db,
                    ticket_id=svc_ticket.id,
                    partner_id=current_member.id,
                    images=payload.images
                )
        except Exception as svc_err:
            logger.error(f"[VGK-ALERT] ServiceTicket creation warning: {svc_err}")
    else:
        formatted_notes = raw_details or None

    alert = VGKMemberQuickAlert(
        alert_code=alert_code,
        alert_type=alert_type,
        partner_id=current_member.id,
        partner_code=current_member.partner_code,
        partner_name=partner_name,
        partner_phone=phone,
        company_id=current_member.company_id,
        tenant_id=getattr(current_member, "tenant_id", None),
        notes=formatted_notes,
        priority=payload.priority or "High",
        status="PENDING",
        claim_token=claim_token,
        linked_ticket_id=linked_ticket_id,
        created_at=now_ist
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    # Determine public claim URL (dynamic host based on request or production domain)
    base_host = str(request.base_url).rstrip("/")
    if "localhost" in base_host or "127.0.0.1" in base_host:
        claim_url = f"https://www.vgk4u.com/staff/claim-alert?token={claim_token}"
    else:
        claim_url = f"{base_host}/staff/claim-alert?token={claim_token}"

    # Build and dispatch WhatsApp group message to Mynt Sales New + configured targets
    msg_text = format_whatsapp_alert_message(alert, claim_url)
    if linked_ticket_code:
        msg_text = msg_text.replace(
            f"📋 *Request Type*: SUPPORT",
            f"📋 *Request Type*: SUPPORT (Service Ticket *{linked_ticket_code}*)\n"
            f"📂 *Category*: {issue_cat or 'Partner Support'}\n"
            f"📌 *Reason*: {issue_reason or 'Support Assistance'}"
            + (f"\n🖼️ *Attached Images*: {len(saved_attachments)}" if saved_attachments else "")
        )

    wa_dispatch = dispatch_quick_alert_to_whatsapp_groups(
        db=db,
        message_text=msg_text,
        job_id="vgk_member_quick_alert",
        job_name="VGK4U Member Quick Alert Broadcast",
        trigger_type=f"quick_alert_{alert_type.lower()}",
        idempotency_prefix=f"qa_create_{alert.alert_code}"
    )

    enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])[0]
    return {
        "success": True,
        "message": (
            f"Support Ticket {linked_ticket_code} created in Service Module & broadcasted to team!"
            if linked_ticket_code else
            "Application alert dispatched successfully to sales team!"
        ),
        "whatsapp_dispatched": wa_dispatch.get("success", False),
        "linked_ticket_code": linked_ticket_code,
        "alert": enriched
    }


@router.get("/my-status")
def get_member_quick_alerts_status(
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    Returns active alerts (PENDING, CLAIMED, IN_PROGRESS) and recent completed alerts
    for live status tracking on the member dashboard.
    """
    active_alerts = db.query(VGKMemberQuickAlert).options(
        joinedload(VGKMemberQuickAlert.claimed_by_staff),
        joinedload(VGKMemberQuickAlert.processed_by_staff)
    ).filter(
        VGKMemberQuickAlert.partner_id == current_member.id,
        VGKMemberQuickAlert.status.in_(["PENDING", "CLAIMED", "IN_PROGRESS"])
    ).order_by(desc(VGKMemberQuickAlert.id)).all()

    recent_completed = db.query(VGKMemberQuickAlert).options(
        joinedload(VGKMemberQuickAlert.claimed_by_staff),
        joinedload(VGKMemberQuickAlert.processed_by_staff)
    ).filter(
        VGKMemberQuickAlert.partner_id == current_member.id,
        VGKMemberQuickAlert.status.in_(["PROCESSED", "CANCELLED"])
    ).order_by(desc(VGKMemberQuickAlert.id)).limit(5).all()

    active_dicts = enrich_alerts_with_service_tickets(db, [a.to_dict() for a in active_alerts])
    completed_dicts = enrich_alerts_with_service_tickets(db, [a.to_dict() for a in recent_completed])

    return {
        "success": True,
        "has_active": len(active_dicts) > 0,
        "active_alerts": active_dicts,
        "recent_completed": completed_dicts
    }


@router.get("/my-history")
def get_member_quick_alerts_history(
    type: Optional[str] = Query(None, description="APPLICATION or SUPPORT or ALL"),
    status: Optional[str] = Query(None, description="Filter by status: PENDING, CLAIMED, IN_PROGRESS, WAITING_FOR_DETAILS, PROCESSED, CANCELLED"),
    search: Optional[str] = Query(None, description="Search keyword"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    DC Protocol (Oct 2026): Executive History for Member Requests & Support Center.
    Returns paginated items with full executive KPIs, turnaround time (TAT), handling staff, and audit remarks.
    """
    from app.models.ticket import ServiceTicket

    # 1. Base query for alerts
    base_alerts_q = db.query(VGKMemberQuickAlert).options(
        joinedload(VGKMemberQuickAlert.claimed_by_staff),
        joinedload(VGKMemberQuickAlert.processed_by_staff)
    ).filter(VGKMemberQuickAlert.partner_id == current_member.id)
    
    all_alerts = base_alerts_q.order_by(desc(VGKMemberQuickAlert.id)).all()
    enriched_alerts = enrich_alerts_with_service_tickets(db, [a.to_dict() for a in all_alerts])
    
    # 2. Check legacy ServiceTickets for this partner not already linked to an alert
    linked_st_codes = set()
    for ea in enriched_alerts:
        if ea.get("service_ticket_code"):
            linked_st_codes.add(ea["service_ticket_code"])
        if ea.get("linked_ticket_id"):
            linked_st_codes.add(str(ea["linked_ticket_id"]))

    legacy_tickets = db.query(ServiceTicket).filter(ServiceTicket.partner_id == current_member.id).all()
    legacy_items = []
    for lt in legacy_tickets:
        if lt.ticket_id in linked_st_codes:
            continue
        lt_status = 'PROCESSED' if (lt.status or '').lower() in ('resolved', 'closed', 'completed') else (
            'IN_PROGRESS' if (lt.status or '').lower() in ('in progress', 'assigned', 'working') else 'PENDING'
        )
        c_dt = lt.created_date.isoformat() if lt.created_date else None
        legacy_items.append({
            "id": f"st_{lt.id}",
            "alert_code": lt.ticket_id,
            "alert_type": "SUPPORT",
            "display_type": "SUPPORT",
            "partner_id": current_member.id,
            "partner_code": current_member.partner_code,
            "partner_name": current_member.name,
            "partner_phone": current_member.mobile_number or '',
            "notes": f"{lt.issue_category or 'Service Ticket'} — {getattr(lt, 'issue_description', '') or ''}".strip(),
            "priority": lt.priority or "Normal",
            "status": lt_status,
            "claimed_by_staff_name": getattr(lt, 'technician_name', None) or "Service Support Desk",
            "claimed_by_emp_code": None,
            "claimed_at": c_dt,
            "claimed_at_ist": lt.created_date.strftime("%d %b %Y, %I:%M %p IST") if lt.created_date else None,
            "processed_by_staff_name": getattr(lt, 'technician_name', None) or "Service Support Desk",
            "processed_at": lt.resolved_date.isoformat() if getattr(lt, 'resolved_date', None) else None,
            "processed_at_ist": lt.resolved_date.strftime("%d %b %Y, %I:%M %p IST") if getattr(lt, 'resolved_date', None) else None,
            "processing_notes": getattr(lt, 'resolution_notes', None) or f"Customer: {lt.customer_name or '—'} ({lt.customer_phone or '—'})",
            "created_at": c_dt,
            "created_at_ist": lt.created_date.strftime("%d %b %Y, %I:%M %p IST") if lt.created_date else None,
            "service_ticket_code": lt.ticket_id,
            "customer_name": getattr(lt, 'customer_name', None),
            "customer_phone": getattr(lt, 'customer_phone', None),
            "claim_wait_seconds": 0,
            "handling_seconds": 0,
            "total_turnaround_seconds": 0
        })

    unified_stream = enriched_alerts + legacy_items

    # Compute Executive KPIs across all records
    total_all = len(unified_stream)
    total_app = sum(1 for x in unified_stream if x.get("alert_type") == 'APPLICATION')
    total_support = sum(1 for x in unified_stream if x.get("alert_type") in ('SUPPORT', 'IMMEDIATE_SUPPORT'))
    total_pending = sum(1 for x in unified_stream if x.get("status") == 'PENDING')
    total_in_progress = sum(1 for x in unified_stream if x.get("status") in ('CLAIMED', 'IN_PROGRESS', 'WAITING_FOR_DETAILS'))
    total_processed = sum(1 for x in unified_stream if x.get("status") == 'PROCESSED')
    total_cancelled = sum(1 for x in unified_stream if x.get("status") == 'CANCELLED')

    tat_seconds_list = [x.get("total_turnaround_seconds") for x in unified_stream if x.get("status") == 'PROCESSED' and (x.get("total_turnaround_seconds") or 0) > 0]
    avg_tat_minutes = int(sum(tat_seconds_list) / len(tat_seconds_list) / 60) if tat_seconds_list else 0

    filtered = unified_stream
    if type and type.upper() != 'ALL':
        u_type = type.upper().strip()
        if u_type == 'APPLICATION':
            filtered = [x for x in filtered if x.get("alert_type") == 'APPLICATION']
        elif u_type in ('SUPPORT', 'IMMEDIATE_SUPPORT'):
            filtered = [x for x in filtered if x.get("alert_type") in ('SUPPORT', 'IMMEDIATE_SUPPORT')]

    if status and status.upper() != 'ALL':
        u_st = status.upper().strip()
        filtered = [x for x in filtered if x.get("status") == u_st]

    if search:
        s_lower = search.strip().lower()
        filtered = [
            x for x in filtered
            if s_lower in (x.get("alert_code") or '').lower()
            or s_lower in (x.get("notes") or '').lower()
            or s_lower in (x.get("processing_notes") or '').lower()
            or s_lower in (x.get("claimed_by_staff_name") or '').lower()
            or s_lower in (x.get("customer_name") or '').lower()
            or s_lower in (x.get("customer_phone") or '').lower()
        ]

    def get_sort_key(item):
        ca = item.get("created_at") or ''
        return str(ca)

    filtered.sort(key=get_sort_key, reverse=True)

    total_filtered = len(filtered)
    start_idx = (page - 1) * page_size
    paged_data = filtered[start_idx : start_idx + page_size]

    return {
        "success": True,
        "total": total_filtered,
        "page": page,
        "page_size": page_size,
        "kpis": {
            "total_all": total_all,
            "total_app": total_app,
            "total_support": total_support,
            "total_pending": total_pending,
            "total_in_progress": total_in_progress,
            "total_processed": total_processed,
            "total_cancelled": total_cancelled,
            "avg_tat_minutes": avg_tat_minutes
        },
        "data": paged_data
    }


@router.post("/member-cancel")
def cancel_member_quick_alert(
    payload: QuickAlertMemberCancelRequest,
    current_member: OfficialPartner = Depends(get_current_vgk_member),
    db: Session = Depends(get_db)
):
    """
    Allows a VGK4U member to cancel their own Application or Support request.
    """
    q = db.query(VGKMemberQuickAlert).filter(VGKMemberQuickAlert.partner_id == current_member.id)
    if payload.alert_id:
        q = q.filter(VGKMemberQuickAlert.id == payload.alert_id)
    elif payload.token:
        q = q.filter(VGKMemberQuickAlert.claim_token == payload.token)
    else:
        raise HTTPException(status_code=400, detail="alert_id or token is required")

    alert = q.first()
    if not alert:
        raise HTTPException(status_code=404, detail="Request not found")

    if alert.status == "CANCELLED":
        return {"success": True, "message": "Request is already cancelled", "alert": alert.to_dict()}

    now_ist = get_indian_time()
    alert.status = "CANCELLED"
    alert.processed_at = now_ist

    reason_str = (payload.reason or "Cancelled by member").strip()
    timestamp_ist = now_ist.strftime("%d %b, %I:%M %p IST")
    cancel_entry = f"[{timestamp_ist} - Member {alert.partner_name}]: ❌ Cancelled ({reason_str})"
    existing_notes = (alert.processing_notes or "").strip()
    alert.processing_notes = f"{existing_notes}\n{cancel_entry}".strip() if existing_notes else cancel_entry

    sync_linked_service_ticket(db, alert, "CANCELLED", f"Member {alert.partner_name}", reason_str)

    db.commit()
    db.refresh(alert)

    type_disp = "APPLICATION" if alert.alert_type == "APPLICATION" else "SUPPORT"
    cancel_msg = (
        f"❌ *CANCELLED BY MEMBER*: Request *{alert.alert_code}* ({type_disp}) by *{alert.partner_name}* "
        f"({alert.partner_code}) has been cancelled at {now_ist.strftime('%I:%M %p IST')}.\n"
        f"📝 *Reason:* {reason_str}"
    )
    dispatch_quick_alert_to_whatsapp_groups(
        db=db,
        message_text=cancel_msg,
        job_id="vgk_alert_cancelled",
        job_name="VGK4U Quick Alert Cancellation",
        trigger_type="quick_alert_cancelled",
        idempotency_prefix=f"qa_cancel_{alert.alert_code}_{int(now_ist.timestamp())}"
    )

    # Automated lifecycle notification directly to the requester
    try:
        from app.services.whatsapp_request_lifecycle_service import send_request_lifecycle_whatsapp_notification
        type_label = "Member Application" if alert.alert_type == "APPLICATION" else "Support Request"
        req_code_display = f"{type_label} {alert.alert_code}"
        send_request_lifecycle_whatsapp_notification(
            db=db,
            recipient_phone=alert.partner_phone,
            recipient_name=alert.partner_name,
            event_type="CANCELLED",
            request_code=req_code_display,
            notes=reason_str,
            company_id=getattr(alert, "company_id", 1) or 1
        )
    except Exception as req_notif_err:
        logger.warning(f"[VGK-ALERT] Member cancellation notification warning: {req_notif_err}")

    return {
        "success": True,
        "message": f"Request {alert.alert_code} has been cancelled.",
        "alert": enrich_alerts_with_service_tickets(db, [alert.to_dict()])[0]
    }


# ─── Staff Dashboard & Claim Endpoints ────────────────────────────────────────

@router.get("/staff-dashboard")
def get_staff_quick_alerts_dashboard(
    status_filter: Optional[str] = Query(None, description="ALL, PENDING, RECLAIMABLE, RUNNING, PROCESSED, CANCELLED"),
    alert_type: Optional[str] = Query(None, description="ALL, APPLICATION, SUPPORT"),
    date_range: Optional[str] = Query("all", description="today, 7d, 30d, mtd, all"),
    search: Optional[str] = Query(None, description="Search by partner name, code, phone, or alert code"),
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Complete Member Applications & Support Dashboard for Sales Department & Key Leadership staff.
    Returns KPI summary + Service Module ticket counts + enriched list of alerts (all strictly in IST).
    """
    emp = db.query(StaffEmployee).options(
        joinedload(StaffEmployee.department),
        joinedload(StaffEmployee.role),
        joinedload(StaffEmployee.base_company)
    ).filter(StaffEmployee.id == current_user.id).first() or current_user

    is_eligible = is_staff_eligible_for_quick_alerts(emp)
    if not is_eligible:
        return {
            "success": True,
            "is_eligible": False,
            "summary": {
                "total": 0,
                "applications_count": 0,
                "support_count": 0,
                "pending_unclaimed": 0,
                "reclaimable_3h": 0,
                "reclaimable_over_3h": 0,
                "running": 0,
                "running_in_progress": 0,
                "completed": 0,
                "completed_processed": 0,
                "cancelled": 0,
                "cancelled_count": 0,
                "avg_handling_seconds": 0,
                "avg_claim_wait_seconds": 0,
                "service_module": {
                    "total_tickets": 0,
                    "open_tickets": 0,
                    "in_progress_tickets": 0,
                    "resolved_tickets": 0,
                    "partner_support_tickets": 0
                }
            },
            "alerts": []
        }

    q = db.query(VGKMemberQuickAlert).options(
        joinedload(VGKMemberQuickAlert.claimed_by_staff),
        joinedload(VGKMemberQuickAlert.processed_by_staff)
    )

    ist_now = get_indian_time()
    dr = (date_range or "all").lower().strip()
    if dr == "today":
        today_start_ist = ist_now.replace(hour=0, minute=0, second=0, microsecond=0)
        q = q.filter(
            or_(
                VGKMemberQuickAlert.created_at >= today_start_ist,
                VGKMemberQuickAlert.status.in_(["PENDING", "CLAIMED", "IN_PROGRESS", "WAITING_FOR_DETAILS"])
            )
        )
    elif dr == "7d":
        cutoff_ist = ist_now - timedelta(days=7)
        q = q.filter(
            or_(
                VGKMemberQuickAlert.created_at >= cutoff_ist,
                VGKMemberQuickAlert.status.in_(["PENDING", "CLAIMED", "IN_PROGRESS", "WAITING_FOR_DETAILS"])
            )
        )
    elif dr == "30d":
        cutoff_ist = ist_now - timedelta(days=30)
        q = q.filter(
            or_(
                VGKMemberQuickAlert.created_at >= cutoff_ist,
                VGKMemberQuickAlert.status.in_(["PENDING", "CLAIMED", "IN_PROGRESS", "WAITING_FOR_DETAILS"])
            )
        )
    elif dr == "mtd":
        mtd_start_ist = ist_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        q = q.filter(
            or_(
                VGKMemberQuickAlert.created_at >= mtd_start_ist,
                VGKMemberQuickAlert.status.in_(["PENDING", "CLAIMED", "IN_PROGRESS", "WAITING_FOR_DETAILS"])
            )
        )

    if alert_type and alert_type.upper() not in ("ALL", ""):
        at_up = alert_type.upper().strip()
        if at_up == "APPLICATION":
            q = q.filter(VGKMemberQuickAlert.alert_type == "APPLICATION")
        elif at_up in ("SUPPORT", "IMMEDIATE_SUPPORT"):
            q = q.filter(VGKMemberQuickAlert.alert_type.in_(["SUPPORT", "IMMEDIATE_SUPPORT"]))

    if search and search.strip():
        s_term = f"%{search.strip()}%"
        q = q.filter(
            or_(
                VGKMemberQuickAlert.alert_code.ilike(s_term),
                VGKMemberQuickAlert.partner_name.ilike(s_term),
                VGKMemberQuickAlert.partner_code.ilike(s_term),
                VGKMemberQuickAlert.partner_phone.ilike(s_term),
                VGKMemberQuickAlert.notes.ilike(s_term)
            )
        )

    all_matching = q.order_by(
        desc(VGKMemberQuickAlert.created_at)
    ).limit(300).all()

    all_dicts = enrich_alerts_with_service_tickets(db, [a.to_dict() for a in all_matching])
    svc_counts = get_service_module_counts(db)

    # Compute KPI summary across all matching rows before status tab filter
    apps_cnt = sum(1 for d in all_dicts if d["alert_type"] == "APPLICATION")
    supp_cnt = sum(1 for d in all_dicts if d["alert_type"] != "APPLICATION")
    pending_cnt = sum(1 for d in all_dicts if d["status"] == "PENDING")
    running_cnt = sum(1 for d in all_dicts if d["status"] in ("CLAIMED", "IN_PROGRESS"))
    waiting_cnt = sum(1 for d in all_dicts if d["status"] == "WAITING_FOR_DETAILS")
    completed_cnt = sum(1 for d in all_dicts if d["status"] == "PROCESSED")
    cancelled_cnt = sum(1 for d in all_dicts if d["status"] == "CANCELLED")
    reclaimable_cnt = sum(1 for d in all_dicts if d.get("is_reclaimable_3h"))

    # Support-specific sub-counts
    support_open_cnt = sum(1 for d in all_dicts if d["alert_type"] != "APPLICATION" and d["status"] == "PENDING")
    support_running_cnt = sum(1 for d in all_dicts if d["alert_type"] != "APPLICATION" and d["status"] in ("CLAIMED", "IN_PROGRESS", "WAITING_FOR_DETAILS"))
    support_resolved_cnt = sum(1 for d in all_dicts if d["alert_type"] != "APPLICATION" and d["status"] == "PROCESSED")

    completed_handling_times = [
        d["handling_seconds"] for d in all_dicts
        if d["status"] == "PROCESSED" and d.get("handling_seconds") is not None
    ]
    avg_handling_sec = int(sum(completed_handling_times) / len(completed_handling_times)) if completed_handling_times else 0

    claim_wait_times = [
        d["claim_wait_seconds"] for d in all_dicts
        if d.get("claimed_at") and d.get("claim_wait_seconds") is not None
    ]
    avg_claim_wait_sec = int(sum(claim_wait_times) / len(claim_wait_times)) if claim_wait_times else 0

    # Apply status filter if requested
    sf = (status_filter or "ALL").upper().strip()
    if sf == "PENDING":
        filtered_dicts = [d for d in all_dicts if d["status"] == "PENDING"]
    elif sf == "RECLAIMABLE":
        filtered_dicts = [d for d in all_dicts if d.get("is_reclaimable_3h")]
    elif sf in ("RUNNING", "IN_PROGRESS", "CLAIMED"):
        filtered_dicts = [d for d in all_dicts if d["status"] in ("CLAIMED", "IN_PROGRESS")]
    elif sf in ("WAITING_FOR_DETAILS", "WAITING", "HOLD"):
        filtered_dicts = [d for d in all_dicts if d["status"] == "WAITING_FOR_DETAILS"]
    elif sf in ("PROCESSED", "COMPLETED"):
        filtered_dicts = [d for d in all_dicts if d["status"] == "PROCESSED"]
    elif sf in ("CANCELLED", "CANCELED"):
        filtered_dicts = [d for d in all_dicts if d["status"] == "CANCELLED"]
    else:
        filtered_dicts = all_dicts

    staff_name = getattr(current_user, "full_name", "") or getattr(current_user, "username", "")
    return {
        "success": True,
        "is_eligible": True,
        "current_staff_id": current_user.id,
        "current_staff_name": staff_name,
        "current_staff": {
            "id": current_user.id,
            "name": staff_name,
            "emp_code": getattr(current_user, "emp_code", "") or ""
        },
        "summary": {
            "total": len(all_dicts),
            "applications_count": apps_cnt,
            "support_count": supp_cnt,
            "support_open": support_open_cnt,
            "support_running": support_running_cnt,
            "support_resolved": support_resolved_cnt,
            "pending_unclaimed": pending_cnt,
            "reclaimable_3h": reclaimable_cnt,
            "reclaimable_over_3h": reclaimable_cnt,
            "running": running_cnt,
            "running_in_progress": running_cnt,
            "waiting_for_details": waiting_cnt,
            "completed": completed_cnt,
            "completed_processed": completed_cnt,
            "cancelled": cancelled_cnt,
            "cancelled_count": cancelled_cnt,
            "avg_handling_seconds": avg_handling_sec,
            "avg_claim_wait_seconds": avg_claim_wait_sec,
            "service_module": svc_counts
        },
        "alerts": filtered_dicts
    }


@router.get("/details-by-token")
def get_alert_details_by_token(
    token: str = Query(..., description="Alert claim token"),
    db: Session = Depends(get_db)
):
    """
    Public / staff preview endpoint to fetch alert details before or during claim.
    Safe: only displays non-sensitive request overview keyed by secure 64-char UUID.
    """
    alert = db.query(VGKMemberQuickAlert).options(
        joinedload(VGKMemberQuickAlert.claimed_by_staff),
        joinedload(VGKMemberQuickAlert.processed_by_staff)
    ).filter(VGKMemberQuickAlert.claim_token == token).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert request not found or invalid token")

    enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
    return {
        "success": True,
        "alert": enriched[0] if enriched else alert.to_dict()
    }


@router.post("/claim")
def claim_quick_alert(
    payload: QuickAlertClaimRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Atomic staff claim lock with 3-Hour Re-Claim SLA Rule:
    - First staff member to claim wins.
    - If an alert remains PENDING or CLAIMED/IN_PROGRESS without completion for > 3 hours (10,800 seconds),
      any eligible department staff member can re-claim and take over the request.
    """
    emp = db.query(StaffEmployee).options(
        joinedload(StaffEmployee.department),
        joinedload(StaffEmployee.role)
    ).filter(StaffEmployee.id == current_user.id).first() or current_user

    if not is_staff_eligible_for_quick_alerts(emp):
        raise HTTPException(
            status_code=403,
            detail="Only Sales Department and Key Leadership staff are authorized to claim Member Applications & Support alerts."
        )

    # Concurrency safe row-level lock
    alert = db.query(VGKMemberQuickAlert).filter(
        VGKMemberQuickAlert.claim_token == payload.token
    ).with_for_update().first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert request not found or invalid token")

    now_ist = get_indian_time()
    staff_name = getattr(current_user, "full_name", "") or getattr(current_user, "username", "Staff")
    staff_code = getattr(current_user, "emp_code", "") or ""
    staff_display = f"{staff_name} ({staff_code})" if staff_code else staff_name

    if alert.status in ("PROCESSED", "CANCELLED"):
        enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
        return {
            "success": False,
            "already_claimed": True,
            "is_current_claimant": (alert.claimed_by_staff_id == current_user.id),
            "message": f"This request is already {alert.status}.",
            "alert": enriched[0] if enriched else alert.to_dict()
        }

    # Check if already claimed by someone else
    is_reclaim_3h = False
    prev_claimant_name = None
    if alert.status != "PENDING":
        if alert.claimed_by_staff:
            prev_claimant_name = getattr(alert.claimed_by_staff, "full_name", "") or getattr(alert.claimed_by_staff, "username", "Staff")
        else:
            prev_claimant_name = "Another staff member"

        is_current_claimant = (alert.claimed_by_staff_id == current_user.id)
        if is_current_claimant:
            enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
            return {
                "success": True,
                "already_claimed": True,
                "is_current_claimant": True,
                "message": f"You have already claimed this request ({alert.alert_code}).",
                "alert": enriched[0] if enriched else alert.to_dict()
            }

        # Check 3-hour SLA rule for takeover by another staff member (all naive IST datetimes)
        ref_claim = (alert.claimed_at.replace(tzinfo=None) if alert.claimed_at and alert.claimed_at.tzinfo else alert.claimed_at) or \
                    (alert.created_at.replace(tzinfo=None) if alert.created_at and alert.created_at.tzinfo else alert.created_at) or now_ist
        ref_created = (alert.created_at.replace(tzinfo=None) if alert.created_at and alert.created_at.tzinfo else alert.created_at) or now_ist
        elapsed_since_claim = (now_ist - ref_claim).total_seconds()
        elapsed_since_created = (now_ist - ref_created).total_seconds()

        if elapsed_since_claim >= THREE_HOURS_SECONDS or elapsed_since_created >= THREE_HOURS_SECONDS:
            is_reclaim_3h = True
        else:
            remaining_secs = int(max(0, THREE_HOURS_SECONDS - max(elapsed_since_claim, elapsed_since_created)))
            rem_hrs = remaining_secs // 3600
            rem_mins = (remaining_secs % 3600) // 60
            enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
            return {
                "success": False,
                "already_claimed": True,
                "is_current_claimant": False,
                "message": (
                    f"This alert is currently claimed by {prev_claimant_name}. "
                    f"It can be re-claimed by another staff member if not completed within 3 hours "
                    f"({rem_hrs}h {rem_mins}m remaining)."
                ),
                "alert": enriched[0] if enriched else alert.to_dict()
            }

    # Perform atomic claim or 3-hour SLA re-claim
    alert.status = "CLAIMED"
    alert.claimed_by_staff_id = current_user.id
    alert.claimed_at = now_ist

    timestamp_ist = now_ist.strftime("%d %b, %I:%M %p IST")
    if is_reclaim_3h:
        reclaim_note = f"[{timestamp_ist} - {staff_display}]: 🔄 Re-claimed request after >3 hours pending SLA (previously with {prev_claimant_name})."
    else:
        reclaim_note = f"[{timestamp_ist} - {staff_display}]: ⚡ Claimed request for processing."

    existing_notes = (alert.processing_notes or "").strip()
    alert.processing_notes = f"{existing_notes}\n{reclaim_note}".strip() if existing_notes else reclaim_note

    sync_linked_service_ticket(
        db=db,
        alert=alert,
        new_status="CLAIMED",
        actor_name=staff_display,
        staff_id=current_user.id,
        notes=reclaim_note
    )

    db.commit()
    db.refresh(alert)

    logger.info(
        f"[VGK-ALERT] Alert #{alert.alert_code} {'RE-CLAIMED (>3h SLA)' if is_reclaim_3h else 'claimed'} "
        f"by {staff_name} (ID #{current_user.id})"
    )

    # Confirmation broadcast to WhatsApp group
    type_disp = "APPLICATION" if alert.alert_type == "APPLICATION" else "SUPPORT"
    if is_reclaim_3h:
        ack_text = (
            f"🔄 *RE-CLAIMED (>3h SLA)*: Request *{alert.alert_code}* ({type_disp}) for partner *{alert.partner_name}* "
            f"was pending >3 hours and has now been re-claimed by *{staff_name}* at {now_ist.strftime('%I:%M %p IST')}."
        )
    else:
        ack_text = (
            f"✅ *CLAIMED*: Request *{alert.alert_code}* ({type_disp}) for partner *{alert.partner_name}* "
            f"has been claimed by *{staff_name}* at {now_ist.strftime('%I:%M %p IST')}."
        )

    dispatch_quick_alert_to_whatsapp_groups(
        db=db,
        message_text=ack_text,
        job_id="vgk_alert_claimed_ack",
        job_name="VGK4U Quick Alert Claim Confirmation",
        trigger_type="quick_alert_claimed",
        idempotency_prefix=f"qa_claim_{alert.alert_code}_{current_user.id}_{int(now_ist.timestamp())}"
    )

    # Automated lifecycle notification directly to the requester
    try:
        from app.services.whatsapp_request_lifecycle_service import send_request_lifecycle_whatsapp_notification
        type_label = "Member Application" if alert.alert_type == "APPLICATION" else "Support Request"
        req_code_display = f"{type_label} {alert.alert_code}"
        send_request_lifecycle_whatsapp_notification(
            db=db,
            recipient_phone=alert.partner_phone,
            recipient_name=alert.partner_name,
            event_type="CLAIMED",
            request_code=req_code_display,
            staff_employee=current_user,
            company_id=getattr(alert, "company_id", 1) or 1
        )
    except Exception as req_notif_err:
        logger.warning(f"[VGK-ALERT] Requester claim notification warning: {req_notif_err}")

    enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
    return {
        "success": True,
        "reclaimed_after_3h": is_reclaim_3h,
        "message": (
            f"Successfully re-claimed (>3h SLA)! You are now handling {alert.partner_name}'s request."
            if is_reclaim_3h else
            f"Successfully claimed! You are now handling {alert.partner_name}'s request."
        ),
        "alert": enriched[0] if enriched else alert.to_dict()
    }


@router.post("/update-status")
def update_quick_alert_status(
    payload: QuickAlertUpdateRequest,
    current_user: StaffEmployee = Depends(get_current_staff_user),
    db: Session = Depends(get_db)
):
    """
    Staff updates progress or marks alert as processed / completed / cancelled.
    Reflects live on member's dashboard status tracker, Service Module, and /staff/progress 1st tab.
    """
    alert = db.query(VGKMemberQuickAlert).filter(
        VGKMemberQuickAlert.claim_token == payload.token
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert request not found")

    new_status = payload.status.upper().strip()
    if new_status not in ("IN_PROGRESS", "PROCESSED", "CANCELLED", "CLAIMED", "WAITING_FOR_DETAILS"):
        raise HTTPException(status_code=400, detail="Invalid status value")

    now_ist = get_indian_time()
    if not alert.claimed_by_staff_id and new_status != "CANCELLED":
        alert.claimed_by_staff_id = current_user.id
        alert.claimed_at = now_ist

    # SLA Resolution Timer Pause / Resume Handling
    if new_status == "WAITING_FOR_DETAILS":
        if alert.status != "WAITING_FOR_DETAILS":
            alert.waiting_for_details_at = now_ist
            alert.waiting_notes = payload.notes
    else:
        # If moving out of WAITING_FOR_DETAILS, accumulate paused seconds so they are never counted in SLA
        if alert.waiting_for_details_at:
            w_at = alert.waiting_for_details_at.replace(tzinfo=None) if hasattr(alert.waiting_for_details_at, 'tzinfo') and alert.waiting_for_details_at.tzinfo else alert.waiting_for_details_at
            n_ist = now_ist.replace(tzinfo=None) if hasattr(now_ist, 'tzinfo') and now_ist.tzinfo else now_ist
            paused_secs = max(0, int((n_ist - w_at).total_seconds())) if (n_ist and w_at) else 0
            alert.total_waiting_seconds = (alert.total_waiting_seconds or 0) + paused_secs
            alert.waiting_for_details_at = None
        if new_status in ("IN_PROGRESS", "PROCESSED") and not alert.details_received_at:
            alert.details_received_at = now_ist

    alert.status = new_status
    staff_label = getattr(current_user, "full_name", "") or getattr(current_user, "username", "Staff")
    staff_code = getattr(current_user, "emp_code", "") or ""
    staff_display = f"{staff_label} ({staff_code})" if staff_code else staff_label
    timestamp_ist = now_ist.strftime("%d %b, %I:%M %p IST")

    if new_status == "CANCELLED":
        reason_text = (payload.notes or "Cancelled by staff").strip()
        existing_notes = (alert.processing_notes or "").strip()
        new_entry = f"[{timestamp_ist} - {staff_display}]: ❌ Cancelled ({reason_text})"
        alert.processing_notes = f"{existing_notes}\n{new_entry}".strip() if existing_notes else new_entry
        alert.processed_by_staff_id = current_user.id
        alert.processed_at = now_ist
    elif new_status == "WAITING_FOR_DETAILS":
        wait_text = (payload.notes or "Waiting for missing details/documents").strip()
        existing_notes = (alert.processing_notes or "").strip()
        new_entry = f"[{timestamp_ist} - {staff_display}]: ⏸️ Waiting for details ({wait_text})"
        alert.processing_notes = f"{existing_notes}\n{new_entry}".strip() if existing_notes else new_entry
    elif payload.notes:
        existing_notes = (alert.processing_notes or "").strip()
        new_entry = f"[{timestamp_ist} - {staff_display}]: {payload.notes.strip()}"
        alert.processing_notes = f"{existing_notes}\n{new_entry}".strip() if existing_notes else new_entry

    if new_status == "PROCESSED":
        alert.processed_by_staff_id = current_user.id
        alert.processed_at = now_ist

    if payload.linked_crm_lead_id:
        alert.linked_crm_lead_id = payload.linked_crm_lead_id
    if payload.linked_ticket_id:
        alert.linked_ticket_id = payload.linked_ticket_id

    sync_linked_service_ticket(
        db=db,
        alert=alert,
        new_status=new_status,
        actor_name=staff_display,
        staff_id=current_user.id,
        notes=payload.notes
    )

    db.commit()
    db.refresh(alert)

    if new_status == "CANCELLED":
        type_disp = "APPLICATION" if alert.alert_type == "APPLICATION" else "SUPPORT"
        cancel_msg = (
            f"❌ *CANCELLED*: Request *{alert.alert_code}* ({type_disp}) for partner *{alert.partner_name}* "
            f"has been cancelled by *{staff_display}* at {now_ist.strftime('%I:%M %p IST')}.\n"
            f"📝 *Reason:* {(payload.notes or 'Cancelled by staff').strip()}"
        )
        dispatch_quick_alert_to_whatsapp_groups(
            db=db,
            message_text=cancel_msg,
            job_id="vgk_alert_cancelled",
            job_name="VGK4U Quick Alert Cancellation",
            trigger_type="quick_alert_cancelled",
            idempotency_prefix=f"qa_cancel_{alert.alert_code}_{int(now_ist.timestamp())}"
        )
    elif new_status == "WAITING_FOR_DETAILS":
        type_disp = "APPLICATION" if alert.alert_type == "APPLICATION" else "SUPPORT"
        wait_msg = (
            f"⏸️ *WAITING FOR DETAILS*: Request *{alert.alert_code}* ({type_disp}) for partner *{alert.partner_name}* "
            f"is on hold by *{staff_display}* at {now_ist.strftime('%I:%M %p IST')}.\n"
            f"📋 *Required:* {(payload.notes or 'Details/documents requested from member').strip()}\n"
            f"⏱️ SLA timer has been paused."
        )
        dispatch_quick_alert_to_whatsapp_groups(
            db=db,
            message_text=wait_msg,
            job_id="vgk_alert_waiting_details",
            job_name="VGK4U Quick Alert Waiting Details",
            trigger_type="quick_alert_waiting_details",
            idempotency_prefix=f"qa_wait_{alert.alert_code}_{int(now_ist.timestamp())}"
        )

    # Automated lifecycle notification directly to the requester
    try:
        from app.services.whatsapp_request_lifecycle_service import send_request_lifecycle_whatsapp_notification
        type_label = "Member Application" if alert.alert_type == "APPLICATION" else "Support Request"
        req_code_display = f"{type_label} {alert.alert_code}"
        action_url = f"https://www.myntreal.com/api/v1/vgk-quick-alerts/details-given/{alert.alert_code}"
        send_request_lifecycle_whatsapp_notification(
            db=db,
            recipient_phone=alert.partner_phone,
            recipient_name=alert.partner_name,
            event_type=new_status,
            request_code=req_code_display,
            staff_employee=current_user,
            notes=payload.notes,
            company_id=getattr(alert, "company_id", 1) or 1,
            action_link=action_url
        )
    except Exception as req_notif_err:
        logger.warning(f"[VGK-ALERT] Requester status update notification warning: {req_notif_err}")

    enriched = enrich_alerts_with_service_tickets(db, [alert.to_dict()])
    return {
        "success": True,
        "message": f"Alert status updated to {new_status}",
        "alert": enriched[0] if enriched else alert.to_dict()
    }


@router.get("/details-given/{alert_code}", response_class=HTMLResponse)
@router.post("/details-given/{alert_code}")
def confirm_member_details_given(
    alert_code: str,
    db: Session = Depends(get_db)
):
    """
    Public 1-Tap endpoint for customer/member to confirm requested details have been provided.
    Resumes SLA resolution clock, updates status to IN_PROGRESS,
    and alerts both the staff WhatsApp group and the assigned staff member.
    """
    alert = db.query(VGKMemberQuickAlert).filter(
        VGKMemberQuickAlert.alert_code == alert_code.strip()
    ).first()

    if not alert:
        return HTMLResponse(
            status_code=404,
            content="""<!DOCTYPE html>
            <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Request Not Found</title>
            <style>body{font-family:sans-serif;background:#0f172a;color:#fff;text-align:center;padding:40px 20px;}</style>
            </head><body>
            <h2>⚠️ Request Not Found</h2>
            <p>We could not find the specified request. Please verify your reference number.</p>
            </body></html>"""
        )

    now_ist = get_indian_time()
    timestamp_ist = now_ist.strftime("%d %b, %I:%M %p IST")

    # If it was in WAITING_FOR_DETAILS, resume the clock
    already_resumed = False
    if alert.status == "WAITING_FOR_DETAILS":
        if alert.waiting_for_details_at:
            w_at = alert.waiting_for_details_at.replace(tzinfo=None) if hasattr(alert.waiting_for_details_at, 'tzinfo') and alert.waiting_for_details_at.tzinfo else alert.waiting_for_details_at
            n_ist = now_ist.replace(tzinfo=None) if hasattr(now_ist, 'tzinfo') and now_ist.tzinfo else now_ist
            paused_secs = max(0, int((n_ist - w_at).total_seconds())) if (n_ist and w_at) else 0
            alert.total_waiting_seconds = (alert.total_waiting_seconds or 0) + paused_secs
            alert.waiting_for_details_at = None

        alert.details_received_at = now_ist
        alert.status = "IN_PROGRESS"

        existing_notes = (alert.processing_notes or "").strip()
        new_entry = f"[{timestamp_ist} - Member / Customer]: ✅ Details confirmed provided by requester."
        alert.processing_notes = f"{existing_notes}\n{new_entry}".strip() if existing_notes else new_entry

        # Synchronize linked service ticket
        sync_linked_service_ticket(
            db=db,
            alert=alert,
            new_status="IN_PROGRESS",
            actor_name="Customer",
            notes="Customer confirmed details provided"
        )

        db.commit()
        db.refresh(alert)

        # Flash notifications to group and assigned staff
        try:
            from app.services.whatsapp_request_lifecycle_service import send_details_received_notifications
            send_details_received_notifications(db=db, alert=alert)
        except Exception as notif_err:
            logger.warning(f"[DETAILS-GIVEN] Notifications error: {notif_err}")
    else:
        already_resumed = True

    staff_name = "Assigned Support Executive"
    if alert.claimed_by_staff_id:
        try:
            from app.models.staff import StaffEmployee
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == alert.claimed_by_staff_id).first()
            if emp:
                staff_name = getattr(emp, "full_name", "") or getattr(emp, "name", staff_name)
        except Exception:
            pass

    type_label = "Member Application" if alert.alert_type == "APPLICATION" else "Support Request"
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Details Received — {alert.alert_code}</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                * {{ box-sizing: border-box; margin:0; padding:0; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    color: #fff;
                }}
                .card {{
                    background: rgba(30, 41, 59, 0.85);
                    backdrop-filter: blur(12px);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 20px;
                    padding: 32px 24px;
                    max-width: 480px;
                    width: 100%;
                    text-align: center;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                }}
                .icon-wrap {{
                    width: 76px;
                    height: 76px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 36px;
                    color: #fff;
                    margin-bottom: 20px;
                    box-shadow: 0 0 25px rgba(16, 185, 129, 0.5);
                }}
                h1 {{ font-size: 22px; font-weight: 800; margin-bottom: 8px; color: #f8fafc; }}
                p {{ font-size: 14.5px; color: #94a3b8; line-height: 1.5; margin-bottom: 20px; }}
                .badge-box {{
                    background: rgba(15, 23, 42, 0.6);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 24px;
                    text-align: left;
                }}
                .badge-row {{
                    display: flex;
                    justify-content: space-between;
                    font-size: 13.5px;
                    padding: 6px 0;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }}
                .badge-row:last-child {{ border-bottom: none; }}
                .badge-label {{ color: #94a3b8; }}
                .badge-val {{ color: #f1f5f9; font-weight: 700; }}
                .status-chip {{
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 700;
                    background: #10b981;
                    color: #fff;
                }}
                .btn-home {{
                    display: inline-block;
                    width: 100%;
                    padding: 14px 20px;
                    background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
                    color: #fff;
                    text-decoration: none;
                    border-radius: 12px;
                    font-weight: 700;
                    font-size: 15px;
                    transition: transform 0.15s ease;
                }}
                .btn-home:active {{ transform: scale(0.98); }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon-wrap">
                    <i class="fas fa-check"></i>
                </div>
                <h1>Details Confirmed Received!</h1>
                <p>
                    Thank you <strong>{alert.partner_name}</strong>. Your requested information has been registered and the resolution clock has resumed.
                </p>
                <div class="badge-box">
                    <div class="badge-row">
                        <span class="badge-label">Request Ref:</span>
                        <span class="badge-val">{type_label} {alert.alert_code}</span>
                    </div>
                    <div class="badge-row">
                        <span class="badge-label">Assigned Executive:</span>
                        <span class="badge-val">{staff_name}</span>
                    </div>
                    <div class="badge-row">
                        <span class="badge-label">Current Status:</span>
                        <span class="badge-val"><span class="status-chip"><i class="fas fa-play me-1"></i> IN PROGRESS</span></span>
                    </div>
                    <div class="badge-row">
                        <span class="badge-label">Confirmed At:</span>
                        <span class="badge-val">{timestamp_ist}</span>
                    </div>
                </div>
                <a href="https://www.myntreal.com" class="btn-home"><i class="fas fa-arrow-left me-1"></i> Return to MyntReal Portal</a>
            </div>
        </body>
        </html>"""
    )

