"""
WhatsApp Auto-Message Service
Handles automatic WhatsApp sends triggered by system events (CRM, PO, ZXtickets, etc.)
All sends are non-blocking BackgroundTasks and respect VGK pause controls.
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Meta Cloud API config ──────────────────────────────────────────────────────
# [DC-WA-CREDS] Credentials are loaded dynamically from DB (with env var fallback)
# Module-level constants kept as fallback for legacy callers
_ACCESS_TOKEN = os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
_PHONE_NUMBER_ID = os.environ.get("META_WHATSAPP_PHONE_NUMBER_ID", "")
_META_BASE = f"https://graph.facebook.com/v21.0/{_PHONE_NUMBER_ID}/messages"

# In-memory dedup cache: { dedup_key: datetime_sent }
# Prevents duplicate auto-sends within a short window (e.g. CRM welcome messages)
_sent_cache: dict = {}


def _get_meta_creds(db=None):
    """Get live Meta credentials from DB or env vars."""
    if db is not None:
        try:
            from app.services.wa_credentials import get_wa_credentials
            creds = get_wa_credentials(db)
            if creds["access_token"]:
                return creds["access_token"], creds["phone_number_id"]
        except Exception:
            pass
    return _ACCESS_TOKEN, _PHONE_NUMBER_ID

# ── Sentinel: track recently sent event+lead combos (in-process dedup) ─────────
# Key = "event_key:lead_id:phone" → datetime sent
_recent_sends: Dict[str, datetime] = {}
_DEDUP_WINDOW_MINUTES = 60  # don't re-send same event for same lead within 1 hour


def _is_paused(db: Session) -> bool:
    """Check VGK pause state."""
    try:
        from app.models.whatsapp import WhatsAppControl
        ctrl = db.query(WhatsAppControl).first()
        return ctrl.is_paused if ctrl else False
    except Exception:
        return False


def _render_body(body_text: str, context: Dict[str, Any]) -> str:
    """Replace {{variable}} placeholders in template body."""
    result = body_text
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return result


def _is_valid_phone(phone: str) -> bool:
    """
    DC-FIX-INVPHONE-001: Reject obviously invalid / placeholder phone numbers
    before hitting the Meta API. Saves API quota and avoids 131026 errors.
    Rules:
    - Must have exactly 10 digits after stripping country code (+91/91)
    - Must not have any single digit dominating ≥8 of 10 positions
      (catches 9999999999, 9999999901, 1111111111, 0000000000, etc.)
    """
    import re as _re
    from collections import Counter
    digits = _re.sub(r'\D', '', phone)
    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    if len(digits) < 10:
        return False
    core = digits[-10:]
    if max(Counter(core).values()) >= 8:
        return False
    return True


def _build_template_components(template, context: Dict[str, Any]) -> list:
    """
    DC-TMPL-COMPONENTS-001: Build Meta API components array for approved templates.
    Extracts named variables from body_text in order → positional {{1}}, {{2}}, …
    Adds image header component if header_type == 'image' and media URL is set.
    Adds URL button components for each button of type 'url'.
    """
    import re as _re
    components = []

    # ── Header (image) ───────────────────────────────────────────────────────
    if getattr(template, 'header_type', 'none') == 'image':
        img_url = getattr(template, 'header_media_url', None) or ""
        if img_url.startswith("http"):
            components.append({
                "type": "header",
                "parameters": [{"type": "image", "image": {"link": img_url}}]
            })

    # ── Body parameters (named vars in appearance order → positional) ────────
    body_text = getattr(template, 'body_text', '') or ''
    var_names = list(dict.fromkeys(_re.findall(r'\{\{(\w+)\}\}', body_text)))
    if var_names and context:
        body_params = []
        for var in var_names:
            val = str(context.get(var, '') or '').strip() or ' '
            body_params.append({"type": "text", "text": val})
        if body_params:
            components.append({"type": "body", "parameters": body_params})

    # ── Buttons (URL type — dynamic suffix parameter) ─────────────────────────
    buttons = getattr(template, 'buttons', None) or []
    for i, btn in enumerate(buttons):
        if isinstance(btn, dict) and btn.get('type') == 'url':
            url_val = btn.get('url', '')
            if url_val:
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": str(i),
                    "parameters": [{"type": "text", "text": url_val}]
                })

    return components


def _send_meta(phone: str, message: str, template=None, db=None,
               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Send via Meta Cloud API.
    If template has meta_template_name + is_meta_approved → use template type with
    full components (image header, body params, URL buttons).
    Otherwise use free-form text (works within 24h session window).
    DC-FIX-INVPHONE-001: Validates phone before sending.
    DC-TMPL-COMPONENTS-001: Populates components for variable substitution & media.
    """
    # DC-FIX-INVPHONE-001: Reject invalid/placeholder numbers
    if not _is_valid_phone(phone):
        logger.warning("[WA-AUTO] Skipping invalid/placeholder phone: %s", phone)
        return {"success": False, "reason": "invalid_phone_number"}

    # [DC-WA-CREDS] Get live credentials from DB if available
    token, phone_id = _get_meta_creds(db)
    if not token or not phone_id:
        logger.warning("[WA-AUTO] No Meta credentials — skipping send to %s", phone)
        return {"success": False, "reason": "no_credentials"}

    meta_base = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    # Safely normalise to E.164 without country code prefix (91XXXXXXXXXX)
    import re as _re
    _digits = _re.sub(r'\D', '', phone)           # strip all non-digits
    if _digits.startswith('91') and len(_digits) == 12:
        recipient = _digits                        # already 91+10 digits
    else:
        recipient = '91' + _digits[-10:]           # take last 10 digits

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if template and template.meta_template_name and template.is_meta_approved:
        tpl_payload: Dict[str, Any] = {
            "name": template.meta_template_name,
            "language": {"code": template.meta_template_language or "en"},
        }
        # DC-TMPL-COMPONENTS-001: Add components for image header, body vars, buttons
        components = _build_template_components(template, context or {})
        if components:
            tpl_payload["components"] = components
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": tpl_payload,
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message}
        }

    try:
        resp = requests.post(meta_base, json=payload, headers=headers, timeout=10)
        data = resp.json()
        if resp.status_code == 200:
            wamid = data.get("messages", [{}])[0].get("id", "")
            return {"success": True, "wamid": wamid}
        else:
            error = data.get("error", {}).get("message", "Unknown error")
            logger.error("[WA-AUTO] Meta API error for %s: %s", phone, error)
            return {"success": False, "reason": error}
    except Exception as e:
        logger.error("[WA-AUTO] Send exception for %s: %s", phone, str(e))
        return {"success": False, "reason": str(e)}


def _log_message(db: Session, phone: str, message: str, result: Dict, event_key: str,
                 lead_id: Optional[int] = None, staff_id: Optional[int] = None,
                 template_id: Optional[int] = None,
                 sent_by_name: Optional[str] = None, sender_type: Optional[str] = None,
                 message_type: Optional[str] = None):
    """Log auto-send to message_log table.

    message_type: override the stored message_type column. Defaults to
    f"auto_{event_key}" to preserve existing convention for all callers that
    do not pass this argument.
    """
    try:
        from app.models.whatsapp import MessageLog
        # Resolve sender display name if not provided
        if staff_id and not sent_by_name:
            try:
                from app.models.staff import StaffEmployee
                se = db.query(StaffEmployee).get(staff_id)
                if se:
                    sent_by_name = f"{getattr(se,'first_name','')} {getattr(se,'last_name','')}".strip() or getattr(se,'name','') or f"Staff #{staff_id}"
            except Exception:
                sent_by_name = f"Staff #{staff_id}"
        if not sent_by_name:
            sent_by_name = "System/Auto"
        if not sender_type:
            sender_type = "staff" if staff_id else "auto"

        resolved_message_type = message_type if message_type is not None else f"auto_{event_key}"
        log = MessageLog(
            message_sid=result.get("wamid") or f"auto.{event_key}.{phone}.{int(datetime.utcnow().timestamp())}",
            message_type=resolved_message_type,
            mobile_number=phone,
            message_body=message,
            to_number=phone,
            provider="META_WHATSAPP",
            initial_status="sent" if result.get("success") else "failed",
            current_status="sent" if result.get("success") else "failed",
            sent_at=datetime.utcnow() if result.get("success") else None,
            error_message=result.get("reason") if not result.get("success") else None,
            sent_by_staff_id=staff_id,
            sent_by_name=sent_by_name,
            sender_type=sender_type,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error("[WA-AUTO] Log exception: %s", str(e))


def _log_to_crm_note(db: Session, lead_id: int, message: str, event_key: str,
                     staff_id: Optional[int] = None, wamid: Optional[str] = None):
    """Append WhatsApp send as a note in crm_lead_notes (lead history)."""
    try:
        from app.models.crm import CRMLeadNote
        note_text = (
            f"📱 WhatsApp auto-message sent [{event_key}]\n"
            f"{message[:300]}{'...' if len(message) > 300 else ''}"
        )
        if wamid:
            note_text += f"\nDelivery ID: {wamid}"
        note = CRMLeadNote(
            lead_id=lead_id,
            note=note_text,
            created_by_staff_id=staff_id,
            created_at=datetime.utcnow(),
        )
        db.add(note)
        db.commit()
    except Exception as e:
        logger.error("[WA-AUTO] CRM note exception: %s", str(e))


def _dedup_key(event_key: str, identifier: str) -> str:
    return f"{event_key}:{identifier}"


def _is_duplicate(key: str) -> bool:
    """Return True if this event was sent recently (within dedup window)."""
    now = datetime.utcnow()
    _recent_sends.update({k: v for k, v in _recent_sends.items()
                           if now - v < timedelta(minutes=_DEDUP_WINDOW_MINUTES)})
    return key in _recent_sends


def _mark_sent(key: str):
    _recent_sends[key] = datetime.utcnow()


# ── Main public function ───────────────────────────────────────────────────────

def send_auto_whatsapp(
    db: Session,
    event_key: str,
    phone: str,
    context: Dict[str, Any],
    lead_id: Optional[int] = None,
    staff_id: Optional[int] = None,
):
    """
    Fire-and-forget auto WhatsApp send for a system event.
    Call this as a FastAPI BackgroundTask — it does NOT block the response.

    Args:
        db: SQLAlchemy session
        event_key: e.g. 'crm_status_won', 'po_dispatched', 'ticket_raised'
        phone: recipient phone (10-digit or +91 format)
        context: variables for template rendering: {name, status, order_no, ...}
        lead_id: CRM lead ID (for note logging)
        staff_id: initiating staff ID
    """
    if not phone or len(phone.strip()) < 10:
        return

    if _is_paused(db):
        logger.info("[WA-AUTO] Paused — skipping %s for %s", event_key, phone)
        return

    # Dedup check
    dedup = _dedup_key(event_key, f"{lead_id or phone}")
    if _is_duplicate(dedup):
        logger.info("[WA-AUTO] Dedup skip %s", dedup)
        return

    # Find trigger config
    try:
        from app.models.whatsapp import WhatsAppAutoTrigger, WhatsAppTemplate
        trigger = db.query(WhatsAppAutoTrigger).filter_by(
            event_key=event_key, is_enabled=True
        ).first()

        if not trigger:
            logger.debug("[WA-AUTO] No active trigger for %s", event_key)
            return

        template = trigger.template
        if not template or not template.is_active:
            logger.debug("[WA-AUTO] No active template for trigger %s", event_key)
            return

        # Render message
        message = _render_body(template.body_text, context)

        # Send — pass context so Meta template components can be built
        result = _send_meta(phone, message, template, db=db, context=context)
        _mark_sent(dedup)

        # Log
        _log_message(db, phone, message, result, event_key, lead_id, staff_id, template.id)
        if lead_id and result.get("success"):
            _log_to_crm_note(db, lead_id, message, event_key, staff_id, result.get("wamid"))

        logger.info("[WA-AUTO] %s → %s: %s", event_key, phone, "OK" if result.get("success") else "FAIL")

    except Exception as e:
        logger.error("[WA-AUTO] Exception for %s / %s: %s", event_key, phone, str(e))


# ── Direct send (from CRM WhatsApp button / test page) ───────────────────────

def send_direct_whatsapp(
    db: Session,
    phone: str,
    message: str,
    template_id: Optional[int] = None,
    lead_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    campaign_log_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Directly send a WhatsApp message (test page, CRM button, campaign).
    Returns result dict. Logs to message_log and CRM note if lead_id provided.
    """
    if _is_paused(db):
        return {"success": False, "reason": "WhatsApp is paused by VGK control"}

    template = None
    if template_id:
        try:
            from app.models.whatsapp import WhatsAppTemplate
            template = db.query(WhatsAppTemplate).get(template_id)
        except Exception:
            pass

    result = _send_meta(phone, message, template, db=db, context=context)

    # Log with sender info
    _log_message(db, phone, message, result, "direct_send", lead_id, staff_id, template_id,
                 sender_type="staff" if staff_id else "system")
    if lead_id and result.get("success"):
        _log_to_crm_note(db, lead_id, message, "direct_send", staff_id, result.get("wamid"))

    # Update campaign log if applicable
    if campaign_log_id and result.get("success"):
        try:
            from app.models.whatsapp import WhatsAppCampaignLog
            log = db.query(WhatsAppCampaignLog).get(campaign_log_id)
            if log:
                log.status = "sent"
                log.wamid = result.get("wamid")
                log.sent_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error("[WA-DIRECT] Campaign log update error: %s", str(e))

    return result


# ── Staff daily morning reminder ───────────────────────────────────────────────

def send_staff_morning_reminder(db: Session, staff_employee, portal_base_url: str = "https://mnrteam.com"):
    """
    Send a personalised morning WhatsApp to one staff member.
    Called by APScheduler job at 8AM IST every weekday.
    DC-FIX-TRIGGER-001: Respects the is_enabled toggle — if the trigger is disabled
    in the Auto-Triggers UI, this function skips the send entirely.
    DC-FIX-DUPWA-001: Caller (run_staff_morning_reminders) holds a PG advisory lock,
    so this is invoked by only one worker process.
    """
    phone = getattr(staff_employee, 'phone', None)
    name  = getattr(staff_employee, 'full_name', None) or getattr(staff_employee, 'name', 'Team Member')

    if not phone:
        return {"success": False, "reason": "no_phone"}

    if _is_paused(db):
        logger.info("[WA-MORNING] Skipped (paused) for %s", name)
        return {"success": False, "reason": "paused"}

    if not _is_valid_phone(phone):
        logger.warning("[WA-MORNING] Skipping invalid phone %s for %s", phone, name)
        return {"success": False, "reason": "invalid_phone_number"}

    today_ist = datetime.utcnow()
    today_str = today_ist.strftime('%A, %d %B %Y')

    try:
        from app.models.whatsapp import WhatsAppAutoTrigger
        # DC-FIX-TRIGGER-001: Look up trigger without is_enabled filter so we can
        # detect disabled state and skip, rather than falling back to hardcoded text.
        trigger = db.query(WhatsAppAutoTrigger).filter_by(
            event_key='staff_morning_reminder'
        ).first()

        if not trigger:
            logger.warning("[WA-MORNING] No trigger configured for staff_morning_reminder — skipping %s", name)
            return {"success": False, "reason": "no_trigger_configured"}

        if not trigger.is_enabled:
            logger.info("[WA-MORNING] Trigger disabled — skipping %s", name)
            return {"success": False, "reason": "trigger_disabled"}

        template = trigger.template if (trigger.template and trigger.template.is_active) else None

        if template:
            message = _render_body(template.body_text, {
                'name': name,
                'date': today_str,
                'kra_link': f"{portal_base_url}/staff/kra-status",
                'tasks_link': f"{portal_base_url}/staff/tasks",
                'timesheet_link': f"{portal_base_url}/staff/timesheet",
                'dashboard_link': f"{portal_base_url}/staff/dashboard",
            })
        else:
            message = (
                f"🌅 Good morning, {name}!\n\n"
                f"📅 *{today_str}*\n\n"
                f"Here are your quick links for today:\n"
                f"📊 KRA Status: {portal_base_url}/staff/kra-status\n"
                f"✅ My Tasks: {portal_base_url}/staff/tasks\n"
                f"⏱ Timesheet: {portal_base_url}/staff/timesheet\n"
                f"📋 Dashboard: {portal_base_url}/staff/dashboard\n\n"
                f"Have a productive day! 💪"
            )

        result = _send_meta(phone, message, template, db=db)
        _log_message(db, phone, message, result, "staff_morning_reminder", staff_id=staff_employee.id)
        logger.info("[WA-MORNING] %s (%s): %s", name, phone, "OK" if result.get("success") else result.get("reason","FAIL"))
        return result

    except Exception as e:
        logger.error("[WA-MORNING] Error for %s: %s", name, str(e))
        return {"success": False, "reason": str(e)}


def send_lead_welcome(
    db,
    phone: str,
    lead_name: str,
    lead_id: int,
    partner_phone: Optional[str] = None,
    staff_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    DC Protocol Apr 2026: Send bilingual (EN+TE) welcome message to every new lead.
    - partner_phone provided  → use 'lead_welcome_walkin' template (includes showroom number)
    - partner_phone is None   → use 'lead_welcome_general' template (company number hardcoded)
    Non-fatal: any failure is logged but does not break lead creation.
    """
    try:
        if not _is_valid_phone(phone):
            logger.warning("[WA-WELCOME] Invalid phone %s — skipping", phone)
            return {"success": False, "reason": "invalid_phone"}

        event_key = "lead_welcome_walkin" if partner_phone else "lead_welcome_general"

        # Dedup: one welcome per lead
        dedup = _dedup_key(event_key, str(lead_id))
        if dedup in _sent_cache:
            return {"success": False, "reason": "already_sent"}

        from app.models.whatsapp import WhatsAppTemplate
        template = db.query(WhatsAppTemplate).filter_by(slug=event_key, is_active=True).first()
        if not template:
            logger.warning("[WA-WELCOME] Template '%s' not found — skipping", event_key)
            return {"success": False, "reason": "template_not_found"}

        context = {"name": lead_name or "there"}
        if partner_phone:
            context["partner_phone"] = partner_phone
        message = _render_body(template.body_text, context)

        result = _send_meta(phone, message, template, db=db, context=context)
        _log_message(db, phone, message, result, event_key, lead_id=lead_id, staff_id=staff_id, template_id=template.id)

        if result.get("success"):
            _sent_cache[dedup] = datetime.utcnow()
        logger.info("[WA-WELCOME] %s → %s: %s", event_key, phone, "OK" if result.get("success") else result.get("reason", "FAIL"))
        return result
    except Exception as e:
        logger.error("[WA-WELCOME] Exception for %s: %s", phone, str(e))
        return {"success": False, "reason": str(e)}


# ── DC_WA_TEMPLATES_SEED_001: Event-specific auto-send helpers ─────────────────

def send_ticket_created_wa(db: Session, ticket) -> Dict[str, Any]:
    """
    Send WhatsApp to customer when a service ticket is created.
    event_key: ticket_created_customer
    Non-fatal: any failure is logged but never raises.
    """
    try:
        phone = getattr(ticket, 'customer_phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_phone"}
        name = getattr(ticket, 'customer_name', None) or 'Customer'
        ticket_id = getattr(ticket, 'ticket_id', None) or str(getattr(ticket, 'id', ''))
        issue = getattr(ticket, 'issue_category', '') or ''
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='ticket_created_customer',
            phone=phone,
            context={'name': name, 'ticket_id': ticket_id, 'issue': issue, 'date': today_str},
        )
    except Exception as e:
        logger.error("[WA-TICKET-CREATE] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_ticket_closed_wa(db: Session, ticket) -> Dict[str, Any]:
    """
    Send WhatsApp to customer when a service ticket is closed.
    event_key: ticket_closed_customer
    """
    try:
        phone = getattr(ticket, 'customer_phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_phone"}
        name = getattr(ticket, 'customer_name', None) or 'Customer'
        ticket_id = getattr(ticket, 'ticket_id', None) or str(getattr(ticket, 'id', ''))
        issue = getattr(ticket, 'issue_category', '') or ''
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='ticket_closed_customer',
            phone=phone,
            context={'name': name, 'ticket_id': ticket_id, 'issue': issue, 'date': today_str},
        )
    except Exception as e:
        logger.error("[WA-TICKET-CLOSE] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_lead_assigned_staff_wa(
    db: Session,
    lead,
    staff,
    triggered_by_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Notify assigned staff via WhatsApp when a new lead is assigned to them.
    event_key: lead_assigned_staff
    """
    try:
        phone = getattr(staff, 'phone', None)
        if not phone or not _is_valid_phone(phone):
            return {"success": False, "reason": "no_valid_staff_phone"}
        staff_name = getattr(staff, 'full_name', None) or getattr(staff, 'name', '') or 'Team Member'
        lead_name = getattr(lead, 'name', '') or 'Unknown'
        lead_phone = getattr(lead, 'phone', '') or '—'
        source = getattr(lead, 'source', '') or 'General'
        today_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime('%d %b %Y')
        return send_auto_whatsapp(
            db=db,
            event_key='lead_assigned_staff',
            phone=phone,
            context={
                'staff_name': staff_name,
                'lead_name': lead_name,
                'phone': lead_phone,
                'source': source.replace('_', ' ').title(),
                'date': today_str,
            },
            staff_id=triggered_by_id,
        )
    except Exception as e:
        logger.error("[WA-LEAD-ASSIGN] Error: %s", e)
        return {"success": False, "reason": str(e)}


def send_staff_morning_leadership(
    db: Session,
    staff_employee,
    portal_base_url: str = "https://mnrteam.com",
) -> Dict[str, Any]:
    """
    Send morning leadership summary WhatsApp to Key Leadership / EA / VGK Supreme staff.
    Queries real-time DB stats for team snapshot.
    event_key: staff_morning_leadership
    """
    phone = getattr(staff_employee, 'phone', None)
    name = getattr(staff_employee, 'full_name', None) or getattr(staff_employee, 'name', 'Leader')

    if not phone or not _is_valid_phone(phone):
        return {"success": False, "reason": "no_valid_phone"}

    if _is_paused(db):
        return {"success": False, "reason": "paused"}

    try:
        from sqlalchemy import text as _text
        today_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        today_date = today_ist.date()
        today_str = today_ist.strftime('%a, %d %b %Y')
        today_midnight_utc = (today_ist.replace(hour=0, minute=0, second=0, microsecond=0)
                              - timedelta(hours=5, minutes=30))

        stats = db.execute(_text("""
            SELECT
                (SELECT COUNT(*) FROM staff_employees WHERE status='active') AS active_staff,
                (SELECT COUNT(*) FROM staff_tasks
                    WHERE status NOT IN ('completed','cancelled')) AS open_tasks,
                (SELECT COUNT(*) FROM staff_tasks
                    WHERE due_date < :today AND status NOT IN ('completed','cancelled')) AS overdue_tasks,
                (SELECT COUNT(*) FROM crm_leads
                    WHERE status NOT IN ('won','lost')) AS open_leads,
                (SELECT COUNT(*) FROM crm_leads
                    WHERE next_followup_date < :now_utc AND status NOT IN ('won','lost')) AS overdue_leads,
                (SELECT COUNT(*) FROM service_ticket
                    WHERE sub_status NOT IN ('closed')) AS open_tickets,
                (SELECT COUNT(*) FROM service_ticket
                    WHERE sub_status='closed' AND closed_date >= :today_midnight) AS closed_today
        """), {
            'today': today_date,
            'now_utc': datetime.utcnow(),
            'today_midnight': today_midnight_utc,
        }).fetchone()

        context = {
            'name': name,
            'date': today_str,
            'active_staff': str(stats[0] if stats else 0),
            'open_tasks': str(stats[1] if stats else 0),
            'overdue_tasks': str(stats[2] if stats else 0),
            'open_leads': str(stats[3] if stats else 0),
            'overdue_leads': str(stats[4] if stats else 0),
            'open_tickets': str(stats[5] if stats else 0),
            'closed_today': str(stats[6] if stats else 0),
            'portal_url': f"{portal_base_url}/staff/dashboard",
        }

        result = send_auto_whatsapp(
            db=db,
            event_key='staff_morning_leadership',
            phone=phone,
            context=context,
            staff_id=getattr(staff_employee, 'id', None),
        )
        logger.info("[WA-LEADERSHIP-MORNING] %s (%s): %s", name, phone,
                    "OK" if result.get("success") else result.get("reason", "FAIL"))
        return result

    except Exception as e:
        logger.error("[WA-LEADERSHIP-MORNING] Error for %s: %s", name, e)
        return {"success": False, "reason": str(e)}
